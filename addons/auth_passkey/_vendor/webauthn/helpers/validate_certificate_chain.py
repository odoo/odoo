from typing import List, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate
from OpenSSL.crypto import X509, X509Store, X509StoreContext, X509StoreContextError

from .exceptions import InvalidCertificateChain
from .pem_cert_bytes_to_open_ssl_x509 import pem_cert_bytes_to_open_ssl_x509


def validate_certificate_chain(
    *,
    x5c: List[bytes],
    pem_root_certs_bytes: Optional[List[bytes]] = None,
) -> bool:
    """Validate that the certificates in x5c chain back to a known root certificate

    Args:
        `x5c`: X5C certificates from a registration response's attestation statement
        (optional) `pem_root_certs_bytes`: Any additional (PEM-formatted)
        root certificates that may complete the certificate chain

    Raises:
        `helpers.exceptions.InvalidCertificateChain` if chain cannot be validated
    """
    if pem_root_certs_bytes is None or len(pem_root_certs_bytes) < 1:
        # We have no root certs to chain back to, so just pass on validation
        return True

    # Make sure we have at least one certificate to try and link back to a root cert
    if len(x5c) < 1:
        raise InvalidCertificateChain("x5c was empty")

    # Prepare leaf cert
    try:
        leaf_cert_bytes = x5c[0]
        leaf_cert_crypto = load_der_x509_certificate(leaf_cert_bytes, default_backend())
        leaf_cert = X509().from_cryptography(leaf_cert_crypto)
    except Exception as err:
        raise InvalidCertificateChain(f"Could not prepare leaf cert: {err}")

    # Prepare any intermediate certs
    try:
        # May be an empty array, that's fine
        intermediate_certs_bytes = x5c[1:]
        intermediate_certs_crypto = [
            load_der_x509_certificate(cert, default_backend()) for cert in intermediate_certs_bytes
        ]
        intermediate_certs = [X509().from_cryptography(cert) for cert in intermediate_certs_crypto]
    except Exception as err:
        raise InvalidCertificateChain(f"Could not prepare intermediate certs: {err}")

    # Prepare a collection of possible root certificates
    root_certs_store = X509Store()
    try:
        for cert in pem_root_certs_bytes:
            root_certs_store.add_cert(pem_cert_bytes_to_open_ssl_x509(cert))
    except Exception as err:
        raise InvalidCertificateChain(f"Could not prepare root certs: {err}")

    # Load certs into a "context" for validation
    context = X509StoreContext(
        store=root_certs_store,
        certificate=leaf_cert,
        chain=intermediate_certs,
    )

    # Validate the chain (will raise if it can't)
    try:
        context.verify_certificate()
    except X509StoreContextError:
        raise InvalidCertificateChain("Certificate chain could not be validated")

    return True
