from base64 import b64decode
from importlib.metadata import version
from ssl import SSLError

import requests
from OpenSSL.crypto import FILETYPE_PEM, load_certificate
from OpenSSL.crypto import Error as CryptoError
from urllib3.contrib.pyopenssl import inject_into_urllib3
from urllib3.util.ssl_ import create_urllib3_context

from odoo.tools import parse_version

# pyOpenSSL >= 24.3.0 expects native cryptography objects
if parse_version(version('pyOpenSSL')) >= parse_version('24.3.0'):
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    def _load_cert(pem):
        return x509.load_pem_x509_certificate(pem)

    def _load_key(key):
        return load_pem_private_key(key, password=None)
else:
    from OpenSSL.crypto import load_privatekey

    def _load_cert(pem):
        return load_certificate(FILETYPE_PEM, pem)

    def _load_key(key):
        return load_privatekey(FILETYPE_PEM, key)


class CertificateAdapter(requests.adapters.HTTPAdapter):

    def __init__(self, *args, ciphers=None, ca_certificates=None, **kwargs):
        self._context_args = {}
        if ciphers:
            self._context_args['ciphers'] = ciphers
        self.ca_certificates = ca_certificates
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """ We need inject_into_urllib3 as it forces the adapter to use PyOpenSSL.
            With PyOpenSSL, we can further patch the code to make it do what we want
            (with the use of SSLContext)
        """
        # OVERRIDE
        inject_into_urllib3()

        context = create_urllib3_context(**self._context_args)
        if self.ca_certificates:
            for cert in self.ca_certificates:
                try:
                    x509_cert = load_certificate(FILETYPE_PEM, b64decode(cert.pem_certificate))
                    context._ctx.get_cert_store().add_cert(x509_cert)
                except (TypeError, CryptoError) as e:
                    raise SSLError(f"CA certificate {cert.name} is invalid: {e.message}")

        def patched_load_cert_chain(certificate, keyfile=None, password=None):
            certificate = certificate.sudo()
            pem, key = map(b64decode, (certificate.pem_certificate, certificate.private_key_id.pem_key))
            context._ctx.use_certificate(_load_cert(pem))
            context._ctx.use_privatekey(_load_key(key))

        context.load_cert_chain = patched_load_cert_chain

        kwargs['ssl_context'] = context
        super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        """ The original method wants to check for an existing file
            at the cert location. As we use in-memory objects,
            we skip the check and assign it manually.
        """
        # OVERRIDE
        super().cert_verify(conn, url, verify, None)
        conn.cert_file = cert
        conn.key_file = None
