from flask import Flask, jsonify, request
from uuid import uuid4
from blockchain import Blockchain
import sys

# 实例化节点
app = Flask(__name__)

# 为该节点生成一个全局唯一的地址
node_identifier = str(uuid4()).replace('-', '')

# 从命令行参数获取端口号，默认为 5000
port = 5000
if len(sys.argv) > 1:
    port = int(sys.argv[1])

# 实例化区块链
blockchain = Blockchain(port)

@app.route('/mine', methods=['GET'])
def mine():
    # 1. 运行工作量证明算法以获得下一个证明
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 2. 给矿工发放奖励 (sender 为 "0" 表示这是新挖出的币)
    blockchain.add_transaction(
        sender="0",
        receiver=node_identifier,
        amount=1,
    )

    # 3. 构造新区块并将其添加到链中
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    # 检查 POST 数据中是否包含所需字段
    required = ['sender', 'receiver', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # 创建新交易
    index = blockchain.add_transaction(values['sender'], values['receiver'], values['amount'])
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200

if __name__ == '__main__':
    # 监听所有公开 IP，便于局域网内测试
    app.run(host='0.0.0.0', port=port)
