import hashlib
import json
import time
import os
import requests
from urllib.parse import urlparse
from utils import Wallet # 导入 Wallet 工具

class Blockchain:
    def __init__(self, port):
        self.chain = []
        self.pending_transactions = []
        self.nodes = set()
        self.port = port
        self.data_file = f"data/chain_{port}.json"

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
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def verify_transaction(self, transaction):
        """
        验证一个交易的签名是否有效
        """
        if transaction['sender'] == "0":
            # 挖矿奖励交易没有签名
            return True
            
        # 准备用于验证的数据 (不包含签名字段本身)
        data_to_verify = {
            'sender': transaction['sender'],
            'receiver': transaction['receiver'],
            'amount': transaction['amount']
        }
        
        return Wallet.verify(
            public_key_hex=transaction['sender'],
            signature_hex=transaction['signature'],
            data=data_to_verify
        )

    def add_transaction(self, sender_public_key, receiver, amount, signature):
        """
        向交易池添加一笔新交易 (并验证)
        """
        transaction = {
            'sender': sender_public_key,
            'receiver': receiver,
            'amount': amount,
            'signature': signature
        }

        if not self.verify_transaction(transaction):
            print("警告: 收到无效的交易签名，已丢弃。")
            return False

        self.pending_transactions.append(transaction)
        return self.last_block['index'] + 1

    def proof_of_work(self, last_proof):
        """简单的工作量证明算法"""
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """验证证明"""
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def new_block(self, proof, previous_hash, miner_address):
        """
        创建一个新区块并添加到链中
        :param miner_address: 挖矿奖励接收者的公钥 (或ID)
        """
        # 创建挖矿奖励交易 (发送者为 "0", 无需签名)
        reward_tx = {
            'sender': "0",
            'receiver': miner_address,
            'amount': 1, # 挖矿奖励为 1
            'signature': None
        }
        
        # 将奖励交易和待处理交易打包
        transactions_for_block = [reward_tx] + self.pending_transactions

        block = {
            'index': len(self.chain),
            'timestamp': time.time(),
            'transactions': transactions_for_block,
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
            self.nodes.add(parsed_url.path)

    def valid_chain(self, chain):
        """
        检查给定的链是否有效 (包括交易签名)
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            
            # 1. 检查区块的 previous_hash
            if block['previous_hash'] != self.hash(last_block):
                print(f"错误: Block {current_index} Previous Hash 不匹配.")
                return False
                
            # 2. 检查工作量证明
            if not self.valid_proof(last_block['proof'], block['proof']):
                print(f"错误: Block {current_index} PoW 无效.")
                return False
                
            # 3. 检查区块内的所有交易签名
            for tx in block['transactions']:
                if not self.verify_transaction(tx):
                    print(f"错误: Block {current_index} 包含无效的交易签名.")
                    return False

            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """共识算法：解决冲突，使用网络中最长的有效链替换掉我们的链"""
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']

                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except requests.exceptions.RequestException:
                continue

        if new_chain:
            self.chain = new_chain
            self.save_chain()
            return True
        return False

    def save_chain(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        with open(self.data_file, 'w') as f:
            json.dump(self.chain, f, indent=4)

    def load_chain(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                try:
                    self.chain = json.load(f)
                    return True
                except json.JSONDecodeError:
                    return False
        return False
