from types import SimpleNamespace
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from OpenSSL import crypto


def load_key_and_certificates(content, password):
    private_key, certificate, _dummy = pkcs12.load_key_and_certificates(content, password, backend=default_backend())

    def public_key():
        public_key = certificate.public_key()

        def public_numbers():
            public_numbers = public_key.public_numbers()
            return SimpleNamespace(
                n=public_numbers.n,
                e=public_numbers.e,
            )
        return SimpleNamespace(
            public_numbers=public_numbers,
            public_bytes=public_key.public_bytes,
        )

    simple_private_key = SimpleNamespace(
        sign=private_key.sign,
        private_bytes=private_key.private_bytes,
    )

    simple_certificate = SimpleNamespace(
        fingerprint=certificate.fingerprint,
        issuer=SimpleNamespace(
            rfc4514_string=certificate.issuer.rfc4514_string,
            rdns=[
                SimpleNamespace(rfc4514_string=item.rfc4514_string)
                for item in certificate.issuer.rdns
            ],
            get_attributes_for_oid=lambda oid: [
                SimpleNamespace(value=item.value)
                for item in certificate.issuer.get_attributes_for_oid(oid)
            ]
        ),
        not_valid_after=certificate.not_valid_after,
        not_valid_before=certificate.not_valid_before,
        public_key=public_key,
        public_bytes=certificate.public_bytes,
        serial_number=certificate.serial_number,
    )
    return simple_private_key, simple_certificate


def crypto_load_certificate(cer_pem):
    certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
    simple_certificate = SimpleNamespace(
        get_notAfter=certificate.get_notAfter,
        get_notBefore=certificate.get_notBefore,
        get_serial_number=certificate.get_serial_number,
        get_subject=lambda: SimpleNamespace(
            CN=certificate.get_subject().CN,
            serialNumber=certificate.get_subject().serialNumber,
        ),
    )
    return simple_certificate
