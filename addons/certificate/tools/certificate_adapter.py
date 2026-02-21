from base64 import b64decode
from ssl import SSLError

import requests
from OpenSSL.crypto import FILETYPE_PEM, load_certificate, load_privatekey
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
                    x509 = load_certificate(FILETYPE_PEM, b64decode(cert.pem_certificate))
                    context._ctx.get_cert_store().add_cert(x509)
                except (TypeError, CryptoError) as e:
                    raise SSLError(f"CA certificate {cert.name} is invalid: {e.message}")

        kwargs['ssl_context'] = context
        super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        """Keep native cert handling for file paths and support certificate records."""
        # OVERRIDE
        self._patch_ssl_context(conn)
        if self._is_certificate_record(cert):
            # The original method checks for file existence. Our certificate object is in-memory.
            super().cert_verify(conn, url, verify, None)
            conn.cert_file = cert
            conn.key_file = None
        else:
            super().cert_verify(conn, url, verify, cert)

    def get_connection(self, url, proxies=None):
        """ Reads the certificate from a certificate.certificate rather than from the filesystem """
        # OVERRIDE
        conn = super().get_connection(url, proxies=proxies)
        self._patch_ssl_context(conn)
        return conn

    def get_connection_with_tls_context(self, *args, **kwargs):
        # OVERRIDE
        conn = super().get_connection_with_tls_context(*args, **kwargs)
        self._patch_ssl_context(conn)
        return conn

    @staticmethod
    def _is_certificate_record(cert):
        return getattr(cert, '_name', None) == 'certificate.certificate'

    def _patch_ssl_context(self, conn):
        conn_kw = getattr(conn, 'conn_kw', None) or {}
        context = conn_kw.get('ssl_context')
        if not context or getattr(context, '_odoo_patched_load_cert_chain', False):
            return

        original_load_cert_chain = context.load_cert_chain

        def patched_load_cert_chain(certificate, keyfile=None, password=None):
            if not self._is_certificate_record(certificate):
                return original_load_cert_chain(certificate, keyfile, password)

            certificate = certificate.sudo()
            pem_certificate = certificate.with_context(bin_size=False).pem_certificate
            pem_private_key = certificate.private_key_id.with_context(bin_size=False).pem_key
            if not pem_certificate or not pem_private_key:
                raise SSLError(f"Certificate {certificate.name} is invalid.")
            try:
                pem, key = map(b64decode, (pem_certificate, pem_private_key))
                context._ctx.use_certificate(load_certificate(FILETYPE_PEM, pem))
                context._ctx.use_privatekey(load_privatekey(FILETYPE_PEM, key))
            except (TypeError, CryptoError) as e:
                raise SSLError(f"Certificate {certificate.name} is invalid: {e}") from e

        context.load_cert_chain = patched_load_cert_chain
        context._odoo_patched_load_cert_chain = True
