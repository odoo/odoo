import base64
import contextlib
import dataclasses
import datetime
import hashlib
import io
import uuid
from typing import Any
from asn1crypto import cms, algos, core, pem, tsp, x509
import logging

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
    from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
    from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
    from cryptography.x509 import Certificate, load_der_x509_certificate, load_pem_x509_certificate
except ImportError:
    # cryptography 41.0.7 and above is supported
    InvalidSignature = None
    hashes = None
    PrivateKeyTypes = None
    Encoding = None
    load_pem_private_key = None
    ec = None
    padding = None
    rsa = None
    Certificate = None
    load_der_x509_certificate = None
    load_pem_x509_certificate = None

from odoo.addons.base.models.res_company import ResCompany
from odoo.tools.pdf import (
    PdfFileReader,
    IndirectObject,
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    ByteStringObject,
    DecodedStreamObject as StreamObject,
    create_string_object
)

from .incremental_pdf_merge import IncrementalPdfMerge, IndirectObjectsWrapper, get_page_media_box
from .constants import TrailerKeys as TK, PageAttributes as PG, CatalogDictionary as CD, InteractiveFormDictEntries as IF

_logger = logging.getLogger(__name__)


class _SignatureContentsPlaceholder(ByteStringObject):
    """
    A placeholder for the `/Contents` field in a PDF signature.

    We handle the serialization of the object rather than relying on the pypdf library.
    This prevents the library from changing the format (like encrypting it,
    or changing how the hex is formatted).

    It also records the exact byte location of this placeholder in the file. This way,
    the signing tool knows exactly where to inject the final signature later without
    having to search the entire file to find the right spot.
    """
    RAW_LEN = 16 * 1024  # 16 KiB raw - leaves headroom for LTV / timestamped CMS payloads

    def __new__(cls):
        return bytes.__new__(cls, b"\0" * cls.RAW_LEN)

    def __init__(self):
        super().__init__()
        self.hex_start = None  # absolute offset of the first hex char (after '<')
        self.hex_end = None    # absolute offset of '>' (exclusive end of hex)

    def write_to_stream(self, stream, encryption_key=None):
        stream.write(b"<")
        self.hex_start = stream.tell()
        stream.write(b"0" * self.RAW_LEN * 2)  # hex encoding is 2 chars per raw byte
        self.hex_end = stream.tell()
        stream.write(b">")


class _ByteRangePlaceholder(ArrayObject):
    """ ``/ByteRange`` placeholder for the PDF signature dictionary.

    Reserves a fixed-width slot (``[`` followed by spaces and ``]``) and records its
    absolute offsets in the output stream, so while signing we can fill it directly
    without searching for the bracket.
    """
    SLOT_LEN = 60  # total bytes including '[' and ']' (room for four 10-digit ints + spaces)

    def __init__(self):
        super().__init__()
        self.start = None  # absolute offset of '['
        self.end = None    # absolute offset just past ']'

    def write_to_stream(self, stream, encryption_key=None):
        self.start = stream.tell()
        stream.write(b"[" + b" " * (self.SLOT_LEN - 2) + b"]")
        self.end = stream.tell()


@dataclasses.dataclass
class PreparedSignature:
    """ A PDF whose signature increment is written and whose ``/ByteRange`` is computed,
    awaiting only the CMS payload.

    :param pdf_data: The full PDF bytes, with the signature hole still empty.
    :param digest: SHA-256 of the signed byte ranges (the CMS ``message_digest`` value).
    :param hex_start: Absolute offset of the ``/Contents`` hex window.
    :param hex_end: Absolute offset just past the hex window.
    """
    pdf_data: bytearray
    digest: bytes
    hex_start: int
    hex_end: int


# -- ETSI EN 319 122-1 signature-policy-identifier --
# asn1crypto ships neither the structure nor the OID for this signed attribute, so we
# describe the shape here and register it on ``cms.CMSAttribute``.
_SIG_POLICY_ID_OID = '1.2.840.113549.1.9.16.2.15'  # id-aa-ets-sigPolicyId
_SPURI_OID = '1.2.840.113549.1.9.16.5.1'  # id-spq-ets-uri


class _OtherHashAlgAndValue(core.Sequence):
    _fields = [
        ('hash_algorithm', algos.DigestAlgorithm),
        ('hash_value', core.OctetString),
    ]


class _SigPolicyQualifierId(core.ObjectIdentifier):
    _map = {_SPURI_OID: 'spuri'}


class _SigPolicyQualifierInfo(core.Sequence):
    _fields = [
        ('sig_policy_qualifier_id', _SigPolicyQualifierId),
        ('qualifier', core.Any, {'optional': True}),
    ]
    _oid_pair = ('sig_policy_qualifier_id', 'qualifier')
    _oid_specs = {'spuri': core.IA5String}


class _SigPolicyQualifiers(core.SequenceOf):
    _child_spec = _SigPolicyQualifierInfo


class _SignaturePolicyId(core.Sequence):
    _fields = [
        ('sig_policy_id', core.ObjectIdentifier),
        ('sig_policy_hash', _OtherHashAlgAndValue),
        ('sig_policy_qualifiers', _SigPolicyQualifiers, {'optional': True}),
    ]


class _SetOfSignaturePolicyId(core.SetOf):
    _child_spec = _SignaturePolicyId


cms.CMSAttributeType._map[_SIG_POLICY_ID_OID] = 'signature_policy_identifier'
cms.CMSAttribute._oid_specs['signature_policy_identifier'] = _SetOfSignaturePolicyId


# -- ETSI EN 319 122-1 commitment-type-indication (the meaning of the signature) --
_COMMITMENT_TYPE_OID = '1.2.840.113549.1.9.16.2.16'  # id-aa-ets-commitmentType


class CommitmentTypeId:
    """ The standard commitment types a signer can make (RFC 5126 / ETSI EN 319 122-1,
    id-cti arc): what signing the data means. Pass one to :class:`CommitmentType`. """
    PROOF_OF_ORIGIN = '1.2.840.113549.1.9.16.6.1'
    PROOF_OF_RECEIPT = '1.2.840.113549.1.9.16.6.2'
    PROOF_OF_DELIVERY = '1.2.840.113549.1.9.16.6.3'
    PROOF_OF_SENDER = '1.2.840.113549.1.9.16.6.4'
    PROOF_OF_APPROVAL = '1.2.840.113549.1.9.16.6.5'
    PROOF_OF_CREATION = '1.2.840.113549.1.9.16.6.6'


class _CommitmentTypeQualifier(core.Sequence):
    _fields = [
        ('commitment_qualifier_id', core.ObjectIdentifier),
        ('qualifier', core.Any, {'optional': True}),
    ]


class _CommitmentTypeQualifiers(core.SequenceOf):
    _child_spec = _CommitmentTypeQualifier


class _CommitmentTypeIndication(core.Sequence):
    _fields = [
        ('commitment_type_id', core.ObjectIdentifier),
        ('commitment_type_qualifier', _CommitmentTypeQualifiers, {'optional': True}),
    ]


class _SetOfCommitmentTypeIndication(core.SetOf):
    _child_spec = _CommitmentTypeIndication


cms.CMSAttributeType._map[_COMMITMENT_TYPE_OID] = 'commitment_type_indication'
cms.CMSAttribute._oid_specs['commitment_type_indication'] = _SetOfCommitmentTypeIndication


@dataclasses.dataclass(frozen=True)
class SignaturePolicy:
    """ The signature policy a signature is created under, referenced by the CMS
    ``signature-policy-identifier`` signed attribute (ETSI EN 319 122-1).

    :param oid: The policy identifier published by the policy authority.
    :param uri: Where the policy document is published (the SPURI qualifier), if any.
    :param digest: Hash of the policy document, empty when the authority publishes no
        machine-processable form to hash against.
    :param digest_algorithm: The algorithm of ``digest``.
    """
    oid: str
    uri: str | None = None
    digest: bytes = b""
    digest_algorithm: str = "sha256"

    @classmethod
    def from_policy_data(cls, policy_data: dict[str, Any] | None) -> 'SignaturePolicy | None':
        """ The policy a signing service declares, or None when it declares none.

        :param policy_data: ``{'oid', 'uri', 'digest' (standard Base64), 'digest_algorithm'}``
        """
        if not policy_data:
            return None
        return cls(
            oid=policy_data['oid'],
            uri=policy_data.get('uri'),
            digest=base64.b64decode(policy_data['digest']) if policy_data.get('digest') else b"",
            digest_algorithm=policy_data.get('digest_algorithm') or "sha256",
        )

    def _to_attribute(self) -> cms.CMSAttribute:
        policy_id = {
            'sig_policy_id': self.oid,
            'sig_policy_hash': {
                'hash_algorithm': {'algorithm': self.digest_algorithm},
                'hash_value': self.digest,
            },
        }
        if self.uri:
            policy_id['sig_policy_qualifiers'] = [{
                'sig_policy_qualifier_id': 'spuri',
                'qualifier': self.uri,
            }]
        return cms.CMSAttribute({
            'type': 'signature_policy_identifier',
            'values': [_SignaturePolicyId(policy_id)],
        })


@dataclasses.dataclass(frozen=True)
class CommitmentType:
    """ The commitment a signer makes by signing (ETSI EN 319 122-1
    commitment-type-indication): what the signature means (approval, origin, receipt, ...).

    :param oid: The commitment type identifier (e.g. :data:`CommitmentTypeId.PROOF_OF_APPROVAL`).
    :param qualifiers: Optional pairs of ``(qualifier_oid_string, raw_der_bytes)`` to attach extra context to the commitment.
        The value must be raw DER, as the expected ASN.1 structure varies by OID.
    """
    oid: str
    qualifiers: tuple[tuple[str, bytes], ...] = ()

    def _to_attribute(self) -> cms.CMSAttribute:
        indication = {'commitment_type_id': self.oid}
        if self.qualifiers:
            indication['commitment_type_qualifier'] = [
                {'commitment_qualifier_id': qualifier_oid, 'qualifier': core.Any.load(der_value)}
                for qualifier_oid, der_value in self.qualifiers
            ]
        return cms.CMSAttribute({
            'type': 'commitment_type_indication',
            'values': [_CommitmentTypeIndication(indication)],
        })


DEFAULT_DIGEST_ALGORITHM = 'sha256'

# asn1crypto identifies a hash by name, but cryptography's verify needs the algorithm object.
_VERIFICATION_HASHES = {'sha256': hashes.SHA256} if hashes else {}

_SIGNATURE_ALGORITHM_FAMILIES = {'rsa': 'rsa', 'ec': 'ecdsa'}


def _signed_digest_algorithm(signer_cert: x509.Certificate, hash_algo: str) -> str:
    """ The CMS signed-digest algorithm name pairing ``hash_algo`` with the certificate's
    signature family (e.g. ``sha256_ecdsa``).

    A certificate's public-key type fixes the family (an EC key can only produce ECDSA
    signatures, an RSA key only RSA ones). Unsupported key types fail and raises an error.
    """
    try:
        key_type = signer_cert.public_key.algorithm
    except (AttributeError, ValueError) as e:
        raise ValueError(f"Failed to read certificate key: {e}")

    if (key_family := _SIGNATURE_ALGORITHM_FAMILIES.get(key_type)) is None:
        raise ValueError("Unsupported signing key type: %s" % key_type)

    return '%s_%s' % (hash_algo, key_family)


def build_signed_attributes(
        digest: bytes,
        signer_cert: x509.Certificate,
        signature_policy: SignaturePolicy | None = None,
        commitment_type: CommitmentType | None = None,
        hash_algo: str = DEFAULT_DIGEST_ALGORITHM,
) -> cms.CMSAttributes:
    """ Builds the CMS signed attributes (RFC 5652, Section 5.3) covering the document digest.

    The CMS signature value is computed over the DER encoding of these attributes, so
    an external signer must sign ``hashlib.new(hash_algo, attrs.dump())``.

    :param digest: The ``hash_algo`` hash of the signed PDF byte ranges.
    :param signer_cert: The signer's certificate, bound to the signature through the
        ESS signing-certificate-v2 attribute (RFC 5035).
    :param signature_policy: The policy the signature commits to, when the signer must
        reference one explicitly (e.g. a qualified signature).
    :param commitment_type: The commitment the signer makes, encoded as a
        commitment-type-indication (e.g. ``CommitmentType(CommitmentTypeId.PROOF_OF_APPROVAL)``).
    :param hash_algo: The digest algorithm (asn1crypto name) used throughout the signature.
        It must match ``digest`` and the algorithm the signer applies.
    """
    # For a PAdES baseline signature (ETSI EN 319 142-1) the signing time is carried by
    # the signature dictionary's ``/M`` entry, and the ``signing-time`` attribute
    # must not also be present when ``/M`` conveys the time.
    attributes = [
        cms.CMSAttribute({
            'type': 'content_type',
            'values': ['data']
        }),
        cms.CMSAttribute({
            'type': 'cms_algorithm_protection',
            'values': [
                    cms.CMSAlgorithmProtection(
                        {
                            'mac_algorithm': None,
                            'digest_algorithm': cms.DigestAlgorithm(
                                {'algorithm': hash_algo, 'parameters': None}
                            ),
                            'signature_algorithm': cms.SignedDigestAlgorithm({
                                'algorithm': _signed_digest_algorithm(signer_cert, hash_algo),
                                'parameters': None
                            })
                        }
                    )
            ]
        }),
        cms.CMSAttribute({
            'type': 'message_digest',
            'values': [digest],
        }),
        # The ESS signing-certificate-v2 structures live in asn1crypto's tsp module
        cms.CMSAttribute({
            'type': tsp.CMSAttributeType('signing_certificate_v2'),
            'values': [tsp.SigningCertificateV2({
                'certs': [tsp.ESSCertIDv2({
                    'hash_algorithm': algos.DigestAlgorithm({'algorithm': hash_algo}),
                    'cert_hash': hashlib.new(hash_algo, signer_cert.dump()).digest(),
                })],
            })],
        }),
    ]
    if signature_policy is not None:
        attributes.append(signature_policy._to_attribute())
    if commitment_type is not None:
        attributes.append(commitment_type._to_attribute())
    return cms.CMSAttributes(attributes)


def certificate_common_name(certificate_pem: bytes) -> str | None:
    """ The subject common name of the leaf certificate of a PEM chain, or None.

    :param certificate_pem: PEM bytes of a certificate chain, leaf first.
    """
    with contextlib.suppress(AttributeError, StopIteration, ValueError):
        _type_name, _headers, der = next(pem.unarmor(certificate_pem, multiple=True))
        return x509.Certificate.load(der).subject.native.get('common_name')

    return None


def visible_signature_rects(page) -> list[tuple[float, float, float, float]]:
    """ The ``(x0, y0, x1, y1)`` of every signature widget showing an appearance on ``page``. """
    rects = []
    for annotation in (page.get('/Annots') or []):
        annot_obj = annotation.get_object()
        rect = annot_obj.get('/Rect')
        if annot_obj.get('/FT') == '/Sig' and rect and float(rect[3]) - float(rect[1]) > 0:
            rects.append(tuple(float(coordinate) for coordinate in rect))

    return rects


def next_signature_appearance_origin(pdf_raw: bytes, appearance_pdf: PdfFileReader) -> tuple[float, float]:
    """ Bottom-left ``(x, y)`` where the next signature appearance fits on page 1.

    Appearances are laid out in rows from the bottom left of the page. Each one goes to the
    right of the previous one, and a row that is full opens the next one above it, so an
    appearance never covers another.
    """
    margin, gap = 20, 6
    appearance_width = float(abs(appearance_pdf.pages[0].mediabox.width))
    appearance_height = float(abs(appearance_pdf.pages[0].mediabox.height))

    pdf_reader = PdfFileReader(io.BytesIO(pdf_raw), strict=False)
    page_box = get_page_media_box(pdf_reader.pages[0])
    page_left, page_right = float(page_box.left) + margin, float(page_box.right) - margin
    page_bottom, page_top = float(page_box.bottom) + margin, float(page_box.top) - margin
    placed_rects = visible_signature_rects(pdf_reader.pages[0])

    row_bottom = page_bottom
    while row_bottom + appearance_height <= page_top:
        # the appearances this row runs into, ordered from left to right
        row_top = row_bottom + appearance_height
        row_rects = sorted(rect for rect in placed_rects if rect[1] <= row_top and rect[3] >= row_bottom)

        x = page_left
        for rect_left, _rect_bottom, rect_right, _rect_top in row_rects:
            if rect_left <= x + appearance_width and rect_right >= x:
                x = rect_right + gap  # taken, try again on the right of this one
        if x + appearance_width <= page_right:
            return (x, row_bottom)
        if not row_rects:
            break  # wider than the page, no row can ever hold it

        row_bottom = max(rect[3] for rect in row_rects) + gap  # the row is full, open the one above

    return (page_left, page_bottom)  # the page is full, fall back to covering the first appearance


def build_cms_signature(
        signed_attrs: cms.CMSAttributes,
        signature: bytes,
        signer_cert: x509.Certificate,
        cert_chain: list[x509.Certificate] | None = None,
        hash_algo: str = DEFAULT_DIGEST_ALGORITHM,
) -> cms.ContentInfo:
    """ Wraps a signature value and its signed attributes into a detached PKCS#7/CMS
    structure (RFC 5652) ready to be injected into a PDF signature field.

    :param signed_attrs: The attributes returned by :func:`build_signed_attributes`.
    :param signature: The raw signature over their DER encoding, computed with the signer's
        key (ex: RSA PKCS#1 v1.5, ECDSA, etc...) over a ``hash_algo`` digest.
    :param signer_cert: The signer's leaf certificate.
    :param cert_chain: Optional intermediate certificates to embed.
    :param hash_algo: The digest algorithm (asn1crypto name) must match the one used to
        build ``signed_attrs``.
    """
    signer_info = cms.SignerInfo({
        'version': 'v1',
        'digest_algorithm': algos.DigestAlgorithm({'algorithm': hash_algo}),
        'signature_algorithm': algos.SignedDigestAlgorithm({'algorithm': _signed_digest_algorithm(signer_cert, hash_algo)}),
        'signature': signature,
        'sid': cms.SignerIdentifier({
            'issuer_and_serial_number': cms.IssuerAndSerialNumber({
                'issuer': signer_cert.issuer,
                'serial_number': signer_cert.serial_number,
            })
        }),
        'signed_attrs': signed_attrs,
    })

    return cms.ContentInfo({
        'content_type': 'signed_data',
        'content': cms.SignedData({
            'version': 'v1',
            'digest_algorithms': [algos.DigestAlgorithm({'algorithm': hash_algo})],
            'encap_content_info': {
                'content_type': 'data',
                'content': None,
            },
            'certificates': [signer_cert, *(cert_chain or ())],
            'signer_infos': [signer_info],
        }),
    })


def verify_signed_attributes(
        signed_attrs: cms.CMSAttributes,
        signature: bytes,
        signer_cert: x509.Certificate,
        hash_algo: str = DEFAULT_DIGEST_ALGORITHM,
) -> bool:
    """ Checks that ``signature`` is a valid signature over the DER encoding of the signed
    attributes under the certificate's public key, using the algorithm implied by the key
    type (RSA PKCS#1 v1.5 or ECDSA) and ``hash_algo``.

    Returns False on any mismatch or unsupported key type.
    """
    public_key = load_der_x509_certificate(signer_cert.dump()).public_key()
    hash_algo_instance = _VERIFICATION_HASHES[hash_algo]()
    try:
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(signature, signed_attrs.dump(), ec.ECDSA(hash_algo_instance))
        elif isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(signature, signed_attrs.dump(), padding.PKCS1v15(), hash_algo_instance)
        else:
            return False
    except InvalidSignature:
        return False
    return True


class PdfSigner:
    """
    Manages the cryptographic signing of PDF documents using incremental updates.

    This class implements the **PAdES** (PDF Advanced Electronic Signatures) standard basics.
    It performs the following operations:

    1.  **Modification:** Modifies the document by adding a signature field via a form
        (AcroForm) and optionally merges a visual overlay.
    2.  **Signing:** Computes a cryptographic signature (PKCS#7/CMS).
    3.  **Injection:** Inserts the signature into the file without invalidating existing
        signatures (incremental update).

    **References:**
    This implementation adheres to the standards defined in:

    * `ISO 32000-1:2008 <https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf>`_
        (For the general structure of the PDF document).
    * `Digital Signatures in a PDF <https://www.adobe.com/devnet-docs/acrobatetk/tools/DigSig/Acrobat_DigitalSignatures_in_PDF.pdf>`_
        (For the specific structure of the signature dictionary).

    :param pdf_raw: The raw bytes of the original PDF file.
    :param company: The Odoo company record containing the signing certificate/key.
    :param signing_time: Optional datetime to use as the signing timestamp.
                         Defaults to ``datetime.now()``.
    """

    def __init__(self, pdf_raw: bytes, company: ResCompany | None = None, signing_time: datetime.datetime | None = None) -> None:
        self.pdf_raw = pdf_raw
        self.pdf_reader = PdfFileReader(io.BytesIO(pdf_raw), strict=False)
        self.company = company
        self.signing_time = signing_time or datetime.datetime.now(datetime.timezone.utc)

    def pdf_contains_signature(self) -> bool:
        """ Checks if the PDF document contains at least one actively applied digital signature.

        :return: True if at least one applied signature exists, False otherwise.
        """
        form_fields = self.pdf_reader.get_fields()
        if form_fields:
            for field_dict in form_fields.values():
                if field_dict.get("/FT") == "/Sig" and "/V" in field_dict:
                    return True

        return False

    def sign_pdf(self, sig_overlay_pdf: PdfFileReader | None = None, field_name: str | None = None, appearance_origin: tuple[float, float] | None = None) -> bytes | None:
        """ Inject a cryptographic digital signature into the PDF document.

        Computes the CMS payload locally using the company certificate and returns the completed signature.

        :param sig_overlay_pdf: The parsed PDF widget to overlay as the signature appearance.
        :param field_name: The dictionary name for the signature field. If left as
            ``None``, a unique name of the form ``"Odoo Signature <uuid>"`` is
            generated so re-signing the same document never collides with an existing
            ``/T`` field.
        :param appearance_origin: Bottom-left ``(x, y)`` of the appearance on the first
            page. Defaults to the top-right corner when omitted.
        :return: The signed PDF data, or None if cryptographic keys/dependencies are missing.
        """
        if not self.company or not load_pem_x509_certificate:
            return None

        prepared = self.write_signature_placeholder(sig_overlay_pdf, field_name, appearance_origin)
        if prepared is None:
            return None

        cms_content_info = self._get_cms_object(prepared.digest)
        if cms_content_info is None:
            return None

        return self.fill_signature_placeholder(prepared, cms_content_info.dump())

    def write_signature_placeholder(self, sig_overlay_pdf: PdfFileReader | None = None, field_name: str | None = None, appearance_origin: tuple[float, float] | None = None) -> PreparedSignature | None:
        """ Write the signature increment and compute the digest to sign.

        Prepares the signature field, appends the incremental update,
        fills the ``/ByteRange`` and hashes the covered bytes.

        :param sig_overlay_pdf: The parsed PDF widget to overlay as the signature appearance.
        :param field_name: The dictionary name for the signature field, see :meth:`sign_pdf`.
        :param appearance_origin: Bottom-left ``(x, y)`` of the appearance, see :meth:`sign_pdf`.
        :return: The prepared signature, or None if the PDF cannot host a signature.
        """
        # Encrypted PDFs would end up corrupt: the new objects are written in
        # plaintext while the trailer still carries /Encrypt, so readers reject
        # the result.
        if TK.ENCRYPT in self.pdf_reader.trailer:
            _logger.warning("Skipping PDF signature: encrypted PDFs are not supported.")
            return None

        # Need at least one page to host the signature widget.
        if not self.pdf_reader.pages:
            _logger.warning("Skipping PDF signature: the PDF has no pages.")
            return None

        # Make the field name unique so re-signing the same document does not
        # produce duplicate /T entries (which break form validation in strict viewers).
        if field_name is None:
            field_name = f"Odoo Signature {uuid.uuid4()}"

        incremented_objects = {}

        # 1. Normalize PDF annotations in case it wasn't signed before
        self._normalize_unsigned_pdf_annotations()

        # 2. Prepare the Signature Field Structure
        contents_placeholder, byte_range_placeholder = self._setup_form(
            self.pdf_reader, field_name, incremented_objects, sig_overlay_pdf, appearance_origin,
        )

        # 3. Write the Incremental Updated PDF, the placeholders record their own offsets while serializing
        pdf_merger = IncrementalPdfMerge(self.pdf_raw)
        pdf_merger.write_incremented_pdf(self.pdf_reader, incremented_objects)

        # 4. Fill the /ByteRange and hash the covered bytes
        return self._fill_byte_range_and_hash(
            pdf_merger.get_output_stream_value(), contents_placeholder, byte_range_placeholder,
        )

    @staticmethod
    def fill_signature_placeholder(prepared: PreparedSignature, cms_der: bytes) -> bytes:
        """ Inject a CMS payload into the reserved block of a prepared signature.

        :param prepared: The prepared signature returned by :meth:`write_signature_placeholder`.
        :param cms_der: The DER encoding of the CMS signature object.
        :return: The final signed PDF bytes.
        :raises ValueError: If the CMS payload is too large for the reserved buffer.
        """
        signature_hex = cms_der.hex().encode('ascii')

        max_hex_len = prepared.hex_end - prepared.hex_start
        if len(signature_hex) > max_hex_len:
            raise ValueError(f"CMS signature ({len(signature_hex)}) too large for hole ({max_hex_len})")

        prepared.pdf_data[prepared.hex_start:prepared.hex_start + len(signature_hex)] = signature_hex

        return bytes(prepared.pdf_data)

    def _normalize_unsigned_pdf_annotations(self):
        """ Prepares an unsigned PDF for sequential digital signing by normalizing annotations.

        If the document is already signed, this method safely exits to preserve the
        existing cryptographic hashes. For unsigned documents, it runs a discrete
        incremental update to force all page ``/Annots`` arrays into indirect objects.

        This structural normalization ensures that when subsequent signatures are
        applied, only the isolated annotation arrays are modified in the XRef table.
        """
        if not self.pdf_contains_signature():
            pdf_merger = IncrementalPdfMerge(self.pdf_raw)
            pdf_merger.normalize_pages_annotations_to_indirect()
            self.pdf_raw = pdf_merger.get_output_stream_value()
            self.pdf_reader = PdfFileReader(io.BytesIO(self.pdf_raw), strict=False)

    def _setup_form(
            self,
            pdf_reader: PdfFileReader,
            field_name: str,
            incremented_objects: dict[tuple[int, int], Any],
            sig_overlay_pdf: PdfFileReader | None = None,
            appearance_origin: tuple[float, float] | None = None,
    ) -> tuple[_SignatureContentsPlaceholder, _ByteRangePlaceholder]:
        """ Configure the PDF ``/AcroForm`` and create the required Signature Field dictionaries.

        This method mutates the PDF object graph by injecting:
        1. **AcroForm Dictionary:** Enables forms and sets ``SigFlags`` to 3 (Signatures Exist | Append Only).
        2. **Signature Field:** The core field definition (e.g., ``/FT /Sig``).
        3. **Visual Appearance:** If provided, embeds the ``sig_overlay_pdf`` as a Form XObject widget.
        4. **Signature Value:** A placeholder dictionary (``/Contents`` and ``/ByteRange``) ready for cryptographic injection.

        :param pdf_reader: The reader object holding the current document state.
        :param field_name: The internal name identifier for the signature field.
        :param incremented_objects: Mapping of modified ``(object_id, generation)`` tuples for the incremental save.
        :param sig_overlay_pdf: An optional pre-rendered PDF containing the visual widget overlay.
        """
        indirect_obj_wrapper = IndirectObjectsWrapper()  # A temporary Wrapper for new objects, useful for the indirect traverse
        catalog = pdf_reader.trailer[TK.ROOT]

        # 1. Setup the AcroForm
        acro_form_originally_exist = False
        if CD.ACRO_FORM not in catalog:
            acro_form = DictionaryObject()
            acro_form.update({
                NameObject(IF.SigFlags): NumberObject(3)
            })
            catalog[NameObject(CD.ACRO_FORM)] = indirect_obj_wrapper.add_object(acro_form)
        else:
            acro_form_originally_exist = True
            acro_form = catalog[CD.ACRO_FORM].get_object()
            # Update flags: Allow Append Mode (Bit 2) | Signatures Exist (Bit 1) = 3
            if IF.SigFlags not in acro_form:
                acro_form[NameObject(IF.SigFlags)] = NumberObject(3)
            else:
                current_flags = acro_form[IF.SigFlags]
                acro_form[NameObject(IF.SigFlags)] = NumberObject(int(current_flags) | 3)

        # 2. Define the signature annotation dictionary
        # We create a Widget Annotation that acts as the signature field.
        # Flags=132 (Print + Locked): Visible when printed, cannot be deleted by user.
        page = pdf_reader.pages[0]
        signature_annotation = DictionaryObject()
        signature_annotation.update({
            NameObject("/FT"): NameObject("/Sig"),  # Field Type: Signature
            NameObject("/T"): create_string_object(field_name),
            NameObject("/Type"): NameObject("/Annot"),  # Object Type: Annotation
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/F"): NumberObject(132),  # Flags: Print | Locked
            NameObject("/P"): page.indirect_reference,
        })

        # 3. Construct the visual appearance widget (optional)
        signature_overlay = None
        content_stream = None

        if sig_overlay_pdf:
            signature_overlay = sig_overlay_pdf.pages[0]
            content_stream = signature_overlay.get_contents()

        if content_stream is not None:
            # Extract the font dictionaries and formatting from the overlay
            signature_resources = signature_overlay.get(PG.RESOURCES, DictionaryObject())

            # Determine the exact dimensions of the signature block
            calc_width = float(abs(signature_overlay.mediabox.width))
            calc_height = float(abs(signature_overlay.mediabox.height))

            if appearance_origin is not None:
                # Caller-driven placement from a bottom-left origin.
                x1, y1 = appearance_origin
                x2, y2 = x1 + calc_width, y1 + calc_height
            else:
                # Calculate absolute coordinates on the first page (Top-Right placement)
                origin = get_page_media_box(page).upper_right
                margin = 20

                x2 = int(float(origin[0]) - margin)
                y2 = int(float(origin[1]) - margin)
                x1 = int(x2 - calc_width)
                y1 = int(y2 - calc_height)

            rect = [x1, y1, x2, y2]

            # Build the Form XObject appearance stream dictionary
            # The /BBox uses local coordinates starting at (0,0) for the internal drawing
            signature_appearance_stream = StreamObject()
            signature_appearance_stream.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Form"),
                NameObject("/BBox"): ArrayObject([
                    NumberObject(0), NumberObject(0),
                    NumberObject(calc_width), NumberObject(calc_height)
                ]),
                NameObject("/Resources"): signature_resources
            })

            # Inject the raw, drawing operations
            signature_appearance_stream._data = content_stream.get_data()

            # Wrap the XObject in an Appearance Dictionary (/AP) under the Normal (/N) state
            signature_appearance = DictionaryObject()
            signature_appearance.update({
                NameObject("/N"): signature_appearance_stream
            })

            # Bind the calculated position (/Rect) and the appearance (/AP) to the Annotation
            signature_annotation.update({
                NameObject("/Rect"): ArrayObject([NumberObject(x) for x in rect]),
                NameObject("/AP"): signature_appearance
            })
        else:
            # Invisible signature (Zero-width rect)
            signature_annotation.update({
                NameObject("/Rect"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0), NumberObject(0)])
            })

        # 4. Prepare the signature object placeholders.
        # The custom placeholder types own their serialization (so the serialization
        # form is independent of the pypdf library) and record their absolute byte
        # offsets so we can fill them directly.
        contents_placeholder = _SignatureContentsPlaceholder()
        byte_range_placeholder = _ByteRangePlaceholder()

        signature_object = DictionaryObject()
        signature_object.update({
            NameObject("/Type"): NameObject("/Sig"),
            NameObject("/Contents"): contents_placeholder,
            NameObject("/ByteRange"): byte_range_placeholder,
            NameObject("/Filter"): NameObject("/Adobe.PPKLite"),
            NameObject("/SubFilter"): NameObject("/ETSI.CAdES.detached"),
            NameObject("/M"): create_string_object(self.signing_time.strftime("D:%Y%m%d%H%M%SZ")),
        })

        # Register objects with the temporary wrapper to get references
        signature_annotation_ref = indirect_obj_wrapper.add_object(signature_annotation)
        signature_object_ref = indirect_obj_wrapper.add_object(signature_object)

        # Link signature value dict to the field dict
        signature_annotation.update({
            NameObject("/V"): signature_object_ref
        })

        # 5. Register the signature annotation in the AcroForm fields, and the page annotations

        # Add to /AcroForm /Fields
        try:
            raw_fields = acro_form.raw_get("/Fields")
        except KeyError:
            raw_fields = None
        if isinstance(raw_fields, IndirectObject):
            fields_array = raw_fields.get_object()
            fields_array.append(signature_annotation_ref)
            raw_id = raw_fields.idnum
            raw_gen = raw_fields.generation
            incremented_objects.setdefault((raw_id, raw_gen), fields_array)
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, raw_gen, raw_id, fields_array)
        else:
            if raw_fields is None:
                raw_fields = ArrayObject()
            raw_fields.append(signature_annotation_ref)
            acro_form[NameObject("/Fields")] = raw_fields

        # Add to Page /Annots
        try:
            raw_annots = page.raw_get(PG.ANNOTS)
        except KeyError:
            raw_annots = None
        if isinstance(raw_annots, IndirectObject):
            annots_array = raw_annots.get_object()
            annots_array.append(signature_annotation_ref)
            raw_id = raw_annots.idnum
            raw_gen = raw_annots.generation
            incremented_objects.setdefault((raw_id, raw_gen), annots_array)
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, raw_gen, raw_id, annots_array)
        else:
            if raw_annots is None:
                raw_annots = ArrayObject()
            raw_annots.append(signature_annotation_ref)
            page[NameObject(PG.ANNOTS)] = raw_annots

            page_ref_id = page.indirect_reference.idnum
            page_ref_gen = page.indirect_reference.generation
            incremented_objects.setdefault((page_ref_id, page_ref_gen), page)
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, page_ref_gen, page_ref_id, page)

        root_entry = pdf_reader.trailer.raw_get(TK.ROOT)
        if isinstance(root_entry, IndirectObject):
            # If Root is indirect, we must explicitly track it for the incremental update
            incremented_objects[root_entry.idnum, root_entry.generation] = catalog
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, root_entry.generation, root_entry.idnum, catalog)

        acro_ref = catalog.raw_get(CD.ACRO_FORM)
        if acro_form_originally_exist and isinstance(acro_ref, IndirectObject):
            incremented_objects[acro_ref.idnum, acro_ref.generation] = acro_form
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, acro_ref.generation, acro_ref.idnum, acro_form)

        return contents_placeholder, byte_range_placeholder

    def _fill_byte_range_and_hash(
            self,
            pdf_data: bytes,
            contents_placeholder: _SignatureContentsPlaceholder,
            byte_range_placeholder: _ByteRangePlaceholder,
    ) -> PreparedSignature:
        """ Fills the ``/ByteRange`` placeholder in place and hashes the signed ranges.

        The offsets recorded by the placeholders during serialization locate the
        signature hole, which is excluded from the hash.

        :param pdf_data: The complete PDF bytes containing the empty signature fields.
        :param contents_placeholder: The serialized ``/Contents`` placeholder.
        :param byte_range_placeholder: The serialized ``/ByteRange`` placeholder.
        :return: The prepared signature awaiting its CMS payload.
        :raises ValueError: If the placeholders were not serialized.
        """
        if contents_placeholder.hex_start is None or byte_range_placeholder.start is None:
            raise ValueError("Signature placeholders were not serialized into the incremental update.")

        pdf_buffer = bytearray(pdf_data)

        # Recover the placeholder slots from the offsets captured at write time
        array_start = byte_range_placeholder.start
        array_end = byte_range_placeholder.end
        placeholder_len = array_end - array_start

        hex_start = contents_placeholder.hex_start
        hex_end = contents_placeholder.hex_end

        # Calculate the signature byte-range values
        # val1: Start of file (always 0)
        # val2: Length of first chunk (up to the opening '<')
        # val3: Offset where second chunk starts (after the closing '>')
        # val4: Length of the second chunk (from val3 to EOF)
        val1 = 0
        val2 = hex_start - 1  # The index of the '<'
        val3 = hex_end + 1  # The index after the '>'
        val4 = len(pdf_buffer) - val3

        # Update the byte-range placeholder and space pad it by transforming  "[0 999...]" into "[0 123 456 789     ]",
        # This keeps the total length IDENTICAL and valid.
        prefix = f"[{val1} {val2} {val3} ".encode('ascii')
        suffix = b"]"

        # Calculate how much room is left for the last number
        # Total Available - Prefix length - Suffix length
        available_len_for_val4 = placeholder_len - len(prefix) - len(suffix)

        if available_len_for_val4 < len(str(val4)):
            raise ValueError(f"Not enough space! Need {len(str(val4))}, have {available_len_for_val4}")

        # Format val4 with trailing spaces
        s_val4 = f"{val4:<{available_len_for_val4}}".encode('ascii')

        # Combine the new byte range
        new_range_str = prefix + s_val4 + suffix

        # Overwrite the buffer
        pdf_buffer[array_start:array_end] = new_range_str

        # We take every byte except the actual signature hex between hex_start-1 and hex_end+1
        data_to_hash = (
                pdf_buffer[val1 : val1 + val2] +
                pdf_buffer[val3 : val3 + val4]
        )
        digest = hashlib.sha256(data_to_hash).digest()

        return PreparedSignature(pdf_buffer, digest, hex_start, hex_end)

    def _get_cms_object(self, digest: bytes) -> cms.ContentInfo | None:
        """ Computes the detached CMS signature payload from the company certificate.

        :param digest: The SHA-256 hash of the relevant PDF byte ranges.
        :return: A CMS object populated with the signature data, or None if the
            company has no valid certificate configured.
        """
        try:
            private_key, leaf_cert, cert_chain = self._load_key_and_certificates()
        except ValueError as e:
            _logger.warning("Skipping PDF signature: Unable to load PEM file. Reason: %s", e)
            return None

        if private_key is None or leaf_cert is None:
            return None

        cert = x509.Certificate.load(leaf_cert.public_bytes(encoding=Encoding.DER))
        chain = [
            x509.Certificate.load(intermediate_cert.public_bytes(encoding=Encoding.DER))
            for intermediate_cert in cert_chain or ()
        ]

        signed_attrs = build_signed_attributes(digest, cert)
        signature = private_key.sign(
            signed_attrs.dump(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return build_cms_signature(signed_attrs, signature, cert, chain)

    def _load_key_and_certificates(self) -> tuple[PrivateKeyTypes | None, Certificate | None, list[Certificate] | None]:
        """ Retrieves and deserializes the private key and certificate from the company record.

        :return: A tuple ``(private_key, leaf_certificate, certificate_chain)``. Returns ``(None, None, None)`` if
                 the company has no valid certificate configured.
        """
        certificate = self.company.signing_certificate_id if "signing_certificate_id" in self.company._fields else None
        if not (certificate and certificate.pem_certificate and certificate.private_key_id and certificate.private_key_id.content):
            return None, None, None

        all_certs = []
        for cert in certificate._get_certificate_chain():
            all_certs.append(load_pem_x509_certificate(cert.pem_certificate.content))

        private_key_bytes = certificate.private_key_id.content.content
        private_key = load_pem_private_key(private_key_bytes, None)

        return private_key, all_certs[0], all_certs[1:]
