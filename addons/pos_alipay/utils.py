# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import rsa
from urllib.parse import quote_plus, unquote_plus


def __add_start_end(key, startMarker, endMarker):
    if key.find(startMarker) < 0:
        key = startMarker + key
    if key.find(endMarker) < 0:
        key = key + endMarker
    return key


def __fill_private_key_marker(private_key):
    return __add_start_end(private_key, "-----BEGIN RSA PRIVATE KEY-----\n", "\n-----END RSA PRIVATE KEY-----")


def __fill_public_key_marker(public_key):
    return __add_start_end(public_key, "-----BEGIN PUBLIC KEY-----\n", "\n-----END PUBLIC KEY-----")


def __sign_with_sha256rsa(private_key, sign_content, charset="UTF-8"):
    sign_content = sign_content.encode(charset)
    private_key = __fill_private_key_marker(private_key)
    signature = rsa.sign(sign_content, rsa.PrivateKey.load_pkcs1(private_key, format='PEM'), 'SHA-256')
    sign_value = str(base64.b64encode(signature), encoding=charset)
    sign_value = quote_plus(sign_value, encoding=charset)
    return sign_value


def __verify_with_sha256rsa(public_key, message, sign_value):
    message = message.encode("UTF-8")
    public_key = __fill_public_key_marker(public_key)
    sign_value = base64.b64decode(sign_value)
    return bool(rsa.verify(message, sign_value, rsa.PublicKey.load_pkcs1_openssl_pem(public_key)))


def gen_sign_content(http_method, path, client_id, time_string, content):
    payload = http_method + " " + path + "\n" + client_id + "." + time_string + "." + content
    return payload


def sign(http_method, path, client_id, req_time_str, req_body, merchant_private_key):
    req_content = gen_sign_content(http_method, path, client_id, req_time_str, req_body)
    private_key = __fill_private_key_marker(merchant_private_key)
    sign_value = __sign_with_sha256rsa(private_key, req_content)
    return sign_value


def verify(http_method, path, client_id, rsp_time_str, rsp_body, signature, alipay_public_key):
    signature = unquote_plus(signature)
    rsp_content = gen_sign_content(http_method, path, client_id, rsp_time_str, rsp_body)
    public_key = __fill_public_key_marker(alipay_public_key)
    is_verify = __verify_with_sha256rsa(public_key, rsp_content, signature)
    return is_verify
