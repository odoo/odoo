from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
from OpenSSL.crypto import X509


def pem_cert_bytes_to_open_ssl_x509(cert: bytes) -> X509:
    """Convert PEM-formatted certificate bytes into an X509 instance usable for cert
    chain validation
    """
    cert_crypto = load_pem_x509_certificate(cert, default_backend())
    cert_openssl = X509().from_cryptography(cert_crypto)
    return cert_openssl
