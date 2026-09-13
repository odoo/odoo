from base64 import b64decode
from ssl import SSLError

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate
from OpenSSL.crypto import X509
from OpenSSL.crypto import Error as CryptoError
from urllib3.contrib.pyopenssl import inject_into_urllib3
from urllib3.util.ssl_ import create_urllib3_context

from odoo.libs import netguard
from odoo.libs.guarded_http import GuardedAdapter


class CertificateAdapter(GuardedAdapter):
    def __init__(
        self,
        *,
        ciphers=None,
        ca_certificates=None,
        policy=netguard.PUBLIC_ONLY,
        **kwargs,
    ):
        self._context_args = {}
        if ciphers:
            self._context_args["ciphers"] = ciphers
        self.ca_certificates = ca_certificates
        super().__init__(policy, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        inject_into_urllib3()

        context = create_urllib3_context(**self._context_args)
        if self.ca_certificates:
            for cert in self.ca_certificates:
                try:
                    x509 = X509.from_cryptography(
                        load_pem_x509_certificate(b64decode(cert.pem_certificate))
                    )
                    context._ctx.get_cert_store().add_cert(x509)
                except (TypeError, CryptoError) as e:
                    raise SSLError(f"CA certificate {cert.name} is invalid: {e}") from e

        kwargs["ssl_context"] = context
        super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        super().cert_verify(conn, url, verify, None)
        conn.cert_file = cert
        conn.key_file = None

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        conn = super().get_connection_with_tls_context(
            request, verify, proxies=proxies, cert=cert
        )
        context = conn.conn_kw["ssl_context"]

        def patched_load_cert_chain(certificate, keyfile=None, password=None):
            certificate = certificate.sudo()
            private_key = certificate.private_key_id
            pem, key = map(
                b64decode,
                (certificate.pem_certificate, private_key.pem_key),
            )
            key_password = (
                private_key.password.encode("utf-8") if private_key.password else None
            )
            context._ctx.use_certificate(load_pem_x509_certificate(pem))
            context._ctx.use_privatekey(
                load_pem_private_key(key, password=key_password)
            )

        context.load_cert_chain = patched_load_cert_chain
        return conn
