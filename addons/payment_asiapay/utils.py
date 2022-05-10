from hashlib import new as hashnew
from .models.const import LANGUAGE_MAPPING

def generate_secure_hash(hash_function: str, merchant_id: str, merchant_reference: str, curr_code: str, amount: str, payment_type: str, secret: str) -> str:
    datas = [merchant_id, merchant_reference, curr_code, amount, payment_type, secret]
    encoded_str = '|'.join(datas).encode()
    shasign = hashnew(hash_function)
    shasign.update(encoded_str)
    return shasign.hexdigest()

def verify_date_feed(secret_hash: str, hash_function: str, src: str, prc: str, success_code: str, merchant_reference: str, paydollar_reference: str, curr_code: str, amount: str, payer_authentication_status: str, secret: str):
    datas = [src, prc, success_code, merchant_reference, paydollar_reference, curr_code, amount, payer_authentication_status, secret]
    encoded_str = '|'.join(datas).encode()
    shasign = hashnew(hash_function)
    shasign.update(encoded_str)
    return shasign.hexdigest() == secret_hash

def get_lang(code: str) -> str:
    country_code = code.split('_')[0]
    lang = LANGUAGE_MAPPING.get(country_code)
    if not lang:
        lang = LANGUAGE_MAPPING.get(code, "E")
    return lang
