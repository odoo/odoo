# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import random
import string
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def generateSignature(params, key):
    params_string = []
    for k in sorted(params.keys()):
        value = params[k] if params[k] is not None and params[k].lower() != "null" else ""
        params_string.append(str(value))
    params = '|'.join(params_string)
    salt = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(4))
    finalString = '%s|%s' % (params, salt)
    hasher = hashlib.sha256(finalString.encode())
    hashString = hasher.hexdigest() + salt
    hashString = bytes(hashString + (16 - len(hashString) % 16) * chr(16 - len(hashString) % 16), 'utf-8')
    key = key.encode("utf8")
    iv = '@@@@&&&&####$$$$'.encode("utf8")
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    hashString = encryptor.update(hashString) + encryptor.finalize()
    hashString = base64.b64encode(hashString)
    return hashString.decode("UTF-8")
