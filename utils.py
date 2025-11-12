import ecdsa
import binascii
import json

class Wallet:
    """
    钱包类，用于生成密钥对、签名和验证
    """
    
    @staticmethod
    def generate_key_pair():
        """
        生成一个新的 ECDSA (secp256k1) 密钥对
        """
        # secp256k1 是比特币使用的曲线
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        private_key = sk.to_string().hex()
        vk = sk.get_verifying_key()
        public_key = vk.to_string().hex()
        return private_key, public_key

    @staticmethod
    def sign(private_key_hex, data):
        """
        使用私钥对数据进行签名
        :param private_key_hex: 16进制的私钥字符串
        :param data: 要签名的数据 (dict)
        :return: 16进制的签名字符串
        """
        try:
            sk_bytes = binascii.unhexlify(private_key_hex)
            sk = ecdsa.SigningKey.from_string(sk_bytes, curve=ecdsa.SECP256k1)
            
            # 我们必须对数据的规范化(有序)表示进行签名
            data_string = json.dumps(data, sort_keys=True).encode()
            signature = sk.sign(data_string)
            return signature.hex()
        except Exception as e:
            print(f"签名失败: {e}")
            return None

    @staticmethod
    def verify(public_key_hex, signature_hex, data):
        """
        使用公钥验证签名
        :param public_key_hex: 16进制的公钥字符串
        :param signature_hex: 16进制的签名字符串
        :param data: 被签名的数据 (dict)
        :return: True/False
        """
        try:
            vk_bytes = binascii.unhexlify(public_key_hex)
            vk = ecdsa.VerifyingKey.from_string(vk_bytes, curve=ecdsa.SECP256k1)
            
            signature_bytes = binascii.unhexlify(signature_hex)
            data_string = json.dumps(data, sort_keys=True).encode()
            
            return vk.verify(signature_bytes, data_string)
        except (binascii.Error, ecdsa.BadSignatureError, Exception) as e:
            # print(f"验证签名失败: {e}")
            return False

def get_hash(data):
    """对一个字典进行 SHA-256 哈希计算 (用于区块哈希)"""
    data_string = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(data_string).hexdigest()
