from base64 import b64decode
from ssl import SSLError

import requests
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate
from OpenSSL.crypto import X509
from OpenSSL.crypto import Error as CryptoError
from urllib3.contrib.pyopenssl import inject_into_urllib3
from urllib3.util.ssl_ import create_urllib3_context


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
                    x509 = X509.from_cryptography(load_pem_x509_certificate(b64decode(cert.pem_certificate)))
                    context._ctx.get_cert_store().add_cert(x509)
                except (TypeError, CryptoError) as e:
                    raise SSLError(f"CA certificate {cert.name} is invalid: {e.message}")

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

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """Load certificate from a certificate.certificate record rather than from the filesystem."""
        # OVERRIDE
        conn = super().get_connection_with_tls_context(request, verify, proxies=proxies, cert=cert)
        context = conn.conn_kw['ssl_context']

        def patched_load_cert_chain(certificate, keyfile=None, password=None):
            certificate = certificate.sudo()
            pem, key = map(b64decode, (certificate.pem_certificate, certificate.private_key_id.pem_key))
            context._ctx.use_certificate(load_pem_x509_certificate(pem))
            context._ctx.use_privatekey(load_pem_private_key(key, password=None))

        context.load_cert_chain = patched_load_cert_chain
        return conn
