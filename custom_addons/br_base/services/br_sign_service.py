import base64
from datetime import date
from typing import Any

try:
    from cryptography.hazmat.primitives.serialization import pkcs12
except ImportError:  # pragma: no cover
    pkcs12 = None

try:
    from signxml import XMLSigner, XMLVerifier
except ImportError:  # pragma: no cover
    XMLSigner = None
    XMLVerifier = None

try:
    from lxml import etree
except ImportError:  # pragma: no cover
    etree = None


class BrSignService:
    def load_cert_a1(self, pfx_bytes: bytes, password: str) -> tuple[Any, Any]:
        if pkcs12 is None:
            raise RuntimeError("Dependencia cryptography nao instalada.")
        cert, key, _additional = pkcs12.load_key_and_certificates(
            pfx_bytes,
            (password or "").encode(),
        )
        return cert, key

    def extract_certificate_metadata(self, pfx_field_value: bytes | str, password: str) -> dict[str, Any]:
        if isinstance(pfx_field_value, str):
            pfx_bytes = base64.b64decode(pfx_field_value)
        else:
            pfx_bytes = pfx_field_value
        cert, _key = self.load_cert_a1(pfx_bytes, password)
        subject = cert.subject.rfc4514_string() if cert else ""
        common_name = next((part.split("=", 1)[1] for part in subject.split(",") if part.startswith("CN=")), "")
        validade = cert.not_valid_after.date() if cert else date.today()
        return {"titular": common_name, "validade": validade}

    def sign_xml(self, xml_bytes: bytes, cert: Any, key: Any, reference_uri: str) -> bytes:
        if etree is None or XMLSigner is None:
            raise RuntimeError("Dependencias de assinatura XML nao instaladas.")
        root = etree.fromstring(xml_bytes)
        signer = XMLSigner(method="enveloped", digest_algorithm="sha256")
        signed = signer.sign(root, key=key, cert=cert, reference_uri=reference_uri)
        return etree.tostring(signed, encoding="utf-8", xml_declaration=True)

    def verify_xml(self, xml_bytes: bytes) -> bool:
        if etree is None or XMLVerifier is None:
            return False
        root = etree.fromstring(xml_bytes)
        XMLVerifier().verify(root)
        return True

