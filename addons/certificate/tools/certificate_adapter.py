from base64 import b64decode

import requests
from OpenSSL.crypto import FILETYPE_PEM, load_certificate, load_privatekey
from urllib3.contrib.pyopenssl import inject_into_urllib3
from urllib3.util.ssl_ import create_urllib3_context


class CertificateAdapter(requests.adapters.HTTPAdapter):

    def __init__(self, *args, ciphers=None, **kwargs):
        self._context_args = {}
        if ciphers:
            self._context_args['ciphers'] = ciphers
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """ We need inject_into_urllib3 as it forces the adapter to use PyOpenSSL.
            With PyOpenSSL, we can further patch the code to make it do what we want
            (with the use of SSLContext)
        """
        # OVERRIDE
        inject_into_urllib3()
        kwargs['ssl_context'] = create_urllib3_context(**self._context_args)
        return super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        """ The original method wants to check for an existing file
            at the cert location. As we use in-memory objects,
            we skip the check and assign it manually.
        """
        # OVERRIDE
        super().cert_verify(conn, url, verify, None)
        conn.cert_file = cert
        conn.key_file = None

    def get_connection(self, url, proxies=None):
        """ Reads the certificate from a certificate.certificate rather than from the filesystem """
        # OVERRIDE
        conn = super().get_connection(url, proxies=proxies)
        context = conn.conn_kw['ssl_context']

        def patched_load_cert_chain(certificate, keyfile=None, password=None):
            certificate = certificate.sudo()
            pem, key = map(b64decode, (certificate.pem_certificate, certificate.private_key_id.pem_key))
            context._ctx.use_certificate(load_certificate(FILETYPE_PEM, pem))
            context._ctx.use_privatekey(load_privatekey(FILETYPE_PEM, key))

        context.load_cert_chain = patched_load_cert_chain
        return conn
