from flask import Flask, jsonify, request
from uuid import uuid4
from blockchain import Blockchain
from utils import Wallet # 导入 Wallet 工具
import sys
import requests

app = Flask(__name__)

# 为该节点生成一个全局唯一的地址 (用于挖矿奖励)
node_identifier = str(uuid4()).replace('-', '')

port = 5000
if len(sys.argv) > 1:
    port = int(sys.argv[1])

blockchain = Blockchain(port)


# --- 钱包 API (用于演示) ---
# 警告: 在真实应用中，私钥永远不应该通过 API 传输!
# 这只是为了方便本教程的演示。

@app.route('/wallet/new', methods=['GET'])
def new_wallet():
    """生成一个新钱包 (密钥对)"""
    private_key, public_key = Wallet.generate_key_pair()
    response = {
        'message': "已创建新钱包",
        'private_key': private_key,
        'public_key': public_key
    }
    return jsonify(response), 200

@app.route('/wallet/sign', methods=['POST'])
def sign_data():
    """(演示用) 传入私钥和数据以获取签名"""
    values = request.get_json()
    required = ['private_key', 'data']
    if not all(k in values for k in required):
        return '缺少参数 (private_key, data)', 400

    private_key = values['private_key']
    data_to_sign = values['data'] # data 应该是一个 dict
    
    signature = Wallet.sign(private_key, data_to_sign)
    
    if signature:
        return jsonify({'signature': signature}), 200
    else:
        return '签名失败', 500


# --- 核心区块链 API ---

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    previous_hash = blockchain.hash(last_block)
    
    # 将 node_identifier (节点ID) 作为挖矿奖励的接收者
    block = blockchain.new_block(proof, previous_hash, node_identifier)

    response = {
        'message': "新区块已挖出",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    
    # 检查 POST 数据中是否包含所需字段 (现在包括签名)
    required = ['sender_public_key', 'receiver', 'amount', 'signature']
    if not all(k in values for k in required):
        return '缺少参数 (sender_public_key, receiver, amount, signature)', 400

    # 创建新交易 (将由 blockchain.add_transaction 验证签名)
    success = blockchain.add_transaction(
        sender_public_key=values['sender_public_key'],
        receiver=values['receiver'],
        amount=values['amount'],
        signature=values['signature']
    )
    
    if success:
        index = blockchain.last_block['index'] + 1
        response = {'message': f'交易将进入区块 {index}'}
        return jsonify(response), 201
    else:
        return '交易签名无效', 400

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


# --- P2P 节点 API (Gossip) ---

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    """
    注册新节点，并执行 'Gossip' 协议返回所有已知节点
    """
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "错误: 请提供一个有效的节点列表", 400

    new_nodes_discovered = set()
    for node_url in nodes:
        blockchain.register_node(node_url)
        new_nodes_discovered.add(node_url.replace("http://", ""))
    
    # Gossip 协议: 返回我们所知道的所有节点
    # 这样新节点就可以发现网络中的其他节点
    all_known_nodes = list(blockchain.nodes)
    
    response = {
        'message': '新节点已添加，并返回了网络中的所有已知节点',
        'nodes_added': list(new_nodes_discovered),
        'total_nodes_known': all_known_nodes
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    """共识算法，解决冲突"""
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': '我们的链已被替换为更长的有效链',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': '我们的链是权威链',
            'chain': blockchain.chain
        }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
