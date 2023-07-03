# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import random
import string
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def generate_signature(params_dict, key):
    params_list = []
    for k in sorted(params_dict.keys()):
        value = params_dict[k]
        if value is None or params_dict[k].lower() == "null":
            value = ""
        params_list.append(str(value))
    salt = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(4))
    params_list.append(salt)
    params_with_salt = '|'.join(params_list)
    hashed_params = hashlib.sha256(params_with_salt.encode())
    hashed_params_with_salt = hashed_params.hexdigest() + salt
    padding = 16 - len(hashed_params_with_salt) % 16
    padded_hashed_params_with_salt = bytes(hashed_params_with_salt + padding * chr(padding), 'utf-8')
    key = key.encode("utf8")
    iv = '@@@@&&&&####$$$$'.encode("utf8")
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted_hashed_params = encryptor.update(padded_hashed_params_with_salt) + encryptor.finalize()
    return base64.b64encode(encrypted_hashed_params).decode("UTF-8")
