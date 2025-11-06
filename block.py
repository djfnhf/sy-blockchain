import hashlib
import json
import time
import os
from urllib.parse import urlparse
import requests

class Blockchain:
    def __init__(self, port):
        self.chain = []
        self.pending_transactions = []
        self.nodes = set()
        self.port = port
        self.data_file = f"data/chain_{port}.json"

        # 初始化时尝试从本地加载，如果没有则创建创世区块
        if not self.load_chain():
            self.create_genesis_block()

    def create_genesis_block(self):
        """创建创世区块"""
        genesis_block = {
            'index': 0,
            'timestamp': time.time(),
            'transactions': [],
            'proof': 100,
            'previous_hash': "0"
        }
        genesis_block['hash'] = self.hash(genesis_block)
        self.chain.append(genesis_block)
        self.save_chain()

    @staticmethod
    def hash(block):
        """对区块进行 SHA-256 哈希计算"""
        # 必须确保字典有序，否则哈希值会不一致
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def add_transaction(self, sender, receiver, amount):
        """向交易池添加一笔新交易"""
        self.pending_transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount
        })
        return self.last_block['index'] + 1

    def proof_of_work(self, last_proof):
        """简单的工作量证明算法：寻找一个数 p' 使得 hash(pp') 以 4 个零开头"""
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """验证证明: hash(last_proof, proof) 是否以 4 个零开头?"""
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def new_block(self, proof, previous_hash=None):
        """创建一个新区块并添加到链中"""
        block = {
            'index': len(self.chain),
            'timestamp': time.time(),
            'transactions': self.pending_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        block['hash'] = self.hash(block)

        self.pending_transactions = [] # 重置交易池
        self.chain.append(block)
        self.save_chain() # 持久化保存
        return block

    def register_node(self, address):
        """添加一个新的节点到节点列表"""
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
             # 处理不带 http:// 前缀的情况
            self.nodes.add(parsed_url.path)

    def valid_chain(self, chain):
        """检查给定的链是否有效"""
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            # 1. 检查区块的 previous_hash 是否正确
            if block['previous_hash'] != self.hash(last_block):
                return False
            # 2. 检查工作量证明是否正确
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """共识算法：解决冲突，使用网络中最长的链替换掉我们的链"""
        neighbours = self.nodes
        new_chain = None
        # 我们只寻找比我们当前链更长的链
        max_length = len(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']

                    # 如果发现更长且有效的链，则记录下来
                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except requests.exceptions.RequestException:
                 # 忽略无法连接的节点
                continue

        # 如果找到了更长且有效的链，替换掉我们本地的链
        if new_chain:
            self.chain = new_chain
            self.save_chain()
            return True
        return False

    def save_chain(self):
        """将当前区块链数据保存到本地 JSON 文件"""
        if not os.path.exists('data'):
            os.makedirs('data')
        with open(self.data_file, 'w') as f:
            json.dump(self.chain, f, indent=4)

    def load_chain(self):
        """尝试从本地 JSON 文件加载区块链数据"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                try:
                    self.chain = json.load(f)
                    return True
                except json.JSONDecodeError:
                    return False
        return False