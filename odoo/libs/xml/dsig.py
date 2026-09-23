import hashlib
from base64 import b64encode
from copy import deepcopy

from lxml import etree

from odoo.libs.debug_log import DebugLog

from .parsers import fromstring

__all__ = [
    "EXC_C14N_ALGORITHM",
    "XmlSigError",
    "canonicalize",
    "canonicalize_signed_info",
    "update_reference_digests",
]


_DS_NS = "http://www.w3.org/2000/09/xmldsig#"
EXC_C14N_ALGORITHM = "http://www.w3.org/2001/10/xml-exc-c14n#"

_NSMAP = {"ds": _DS_NS}
_debug = DebugLog(__name__)


class XmlSigError(ValueError):
    pass


def canonicalize(
    node: etree._Element | str,
    *,
    exclusive: bool = False,
    inclusive_ns_prefixes: list[str] | None = None,
) -> bytes:
    if isinstance(node, str):
        node = fromstring(node)
    return etree.tostring(
        node,
        method="c14n",
        with_comments=False,
        exclusive=exclusive,
        inclusive_ns_prefixes=inclusive_ns_prefixes,
    )


def _get_c14n_params_from_transforms(
    reference: etree._Element,
) -> tuple[bool, list[str]]:
    exclusive = next(
        (
            transform
            for transform in reference.findall(".//{*}Transform")
            if transform.get("Algorithm") == EXC_C14N_ALGORITHM
        ),
        None,
    )
    if exclusive is None:
        return False, []
    prefix_list = []
    inclusive_ns = exclusive.find(".//{*}InclusiveNamespaces")
    if inclusive_ns is not None and inclusive_ns.get("PrefixList"):
        prefix_list = inclusive_ns.get("PrefixList").split()
    return True, prefix_list


def _get_enveloping_signatures(
    reference: etree._Element, copied_root: etree._Element
) -> list[etree._Element]:
    tag = f"{{{_DS_NS}}}Signature"
    own = next(reference.iterancestors(tag), None)
    if own is None:
        return list(copied_root.iter(tag))

    originals = list(reference.getroottree().getroot().iter(tag))
    index = next((i for i, sig in enumerate(originals) if sig is own), None)
    if index is None:
        msg = "the reference's enveloping signature is not in its own document"
        raise XmlSigError(msg)

    copies = list(copied_root.iter(tag))
    if index >= len(copies):
        msg = f"signature {index} is missing from the copied document"
        raise XmlSigError(msg)
    return [copies[index]]


def _resolve_reference(uri: str, reference: etree._Element) -> bytes:
    exclusive, prefix_list = _get_c14n_params_from_transforms(reference)
    root = reference.getroottree().getroot()

    if not uri:
        # the enveloped signature is removed from a copy, never from the document
        node = deepcopy(root)
        _debug.logic(
            "dsig.reference",
            kind="enveloped",
            exclusive=exclusive,
            prefixes=len(prefix_list),
        )
        for signature in _get_enveloping_signatures(reference, node):
            if signature.tail:
                if (previous := signature.getprevious()) is not None:
                    previous.tail = (previous.tail or "") + signature.tail
                else:
                    parent = signature.getparent()
                    parent.text = (parent.text or "") + signature.tail
            signature.getparent().remove(signature)
        return canonicalize(
            node, exclusive=exclusive, inclusive_ns_prefixes=prefix_list
        )

    if uri.startswith("#"):
        results = root.xpath('//*[@*[local-name() = "Id"]=$uri]', uri=uri.lstrip("#"))
        _debug.logic(
            "dsig.reference",
            kind="id",
            matches=len(results),
            exclusive=exclusive,
            prefixes=len(prefix_list),
        )
        if len(results) == 1:
            return canonicalize(
                results[0], exclusive=exclusive, inclusive_ns_prefixes=prefix_list
            )
        if len(results) > 1:
            raise XmlSigError(
                f"Ambiguous reference URI {uri!r} resolved to {len(results)} nodes"
            )

    _debug.logic("dsig.reference", kind="unresolved", fragment=uri.startswith("#"))
    raise XmlSigError(f"URI {uri!r} not found")


def canonicalize_signed_info(signed_info: etree._Element) -> bytes:
    method = signed_info.find(".//{*}CanonicalizationMethod")
    exclusive = method is not None and method.get("Algorithm") == EXC_C14N_ALGORITHM
    prefix_list = []
    if exclusive:
        inclusive_ns = method.find(".//{*}InclusiveNamespaces")
        if inclusive_ns is not None and inclusive_ns.get("PrefixList"):
            prefix_list = inclusive_ns.get("PrefixList").split()
    return canonicalize(
        signed_info, exclusive=exclusive, inclusive_ns_prefixes=prefix_list
    )


def update_reference_digests(
    signed_info: etree._Element, *, algorithm: str = "sha256"
) -> None:
    for reference in signed_info.findall("ds:Reference", namespaces=_NSMAP):
        digest_value = reference.find("ds:DigestValue", namespaces=_NSMAP)
        if digest_value is None:
            raise XmlSigError(
                f"Reference {reference.get('URI', '')!r} has no <ds:DigestValue> "
                f"to fill in"
            )
        with _debug.perf("dsig.digest", algorithm=algorithm) as span:
            octets = _resolve_reference(reference.get("URI", ""), reference)
            span.set(octets=len(octets))
            digest = hashlib.new(algorithm, octets).digest()
        digest_value.text = b64encode(digest).decode("ascii")
