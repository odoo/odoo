import hashlib
import re
from base64 import b64encode

import pytest
from lxml import etree

from odoo.libs.xml.dsig import (
    _DS_NS as DS_NS,
)
from odoo.libs.xml.dsig import (
    EXC_C14N_ALGORITHM,
    XmlSigError,
    canonicalize,
    canonicalize_signed_info,
    update_reference_digests,
)
from odoo.libs.xml.dsig import (
    _resolve_reference as resolve_reference,
)

DOC = f"""<Invoice xmlns:ds="{DS_NS}">
  <Line Id="line-1">
    <Amount>100</Amount>
  </Line>
  <ds:Signature>
    <ds:SignedInfo>
      <ds:Reference URI="">
        <ds:Transforms>
          <ds:Transform Algorithm="{DS_NS}enveloped-signature"/>
        </ds:Transforms>
        <ds:DigestValue/>
      </ds:Reference>
      <ds:Reference URI="#line-1">
        <ds:DigestValue/>
      </ds:Reference>
    </ds:SignedInfo>
  </ds:Signature>
</Invoice>
"""


def _tree():
    return etree.fromstring(DOC.encode())


def _signed_info(root):
    return root.find(f"{{{DS_NS}}}Signature/{{{DS_NS}}}SignedInfo")


def _first_reference(root):
    return _signed_info(root).find(f"{{{DS_NS}}}Reference")


class TestEnvelopedStripping:
    def test_signature_is_removed_for_base_uri(self):
        root = _tree()
        octets = resolve_reference("", _first_reference(root))
        assert b"Signature" not in octets
        assert b"<Amount>100</Amount>" in octets

    def test_caller_tree_is_not_mutated(self):
        root = _tree()
        resolve_reference("", _first_reference(root))
        assert root.find(f"{{{DS_NS}}}Signature") is not None

    def test_nested_signature_is_removed(self):
        doc = f'<Invoice xmlns:ds="{DS_NS}"><Ext><ds:Signature Id="s"/></Ext></Invoice>'
        root = etree.fromstring(doc.encode())
        reference = etree.SubElement(root, f"{{{DS_NS}}}Reference")
        octets = resolve_reference("", reference)
        assert b"Signature" not in octets

    def test_only_the_references_own_signature_is_removed(self):
        doc = (
            f'<Invoice xmlns:ds="{DS_NS}"><Amount>100</Amount>'
            f'<ds:Signature><ds:SignedInfo><ds:Reference URI=""/></ds:SignedInfo>'
            f"<ds:SignatureValue>FIRST</ds:SignatureValue></ds:Signature>"
            f'<ds:Signature><ds:SignedInfo><ds:Reference URI=""/></ds:SignedInfo>'
            f"<ds:SignatureValue>SECOND</ds:SignatureValue></ds:Signature>"
            f"</Invoice>"
        )
        root = etree.fromstring(doc.encode())
        references = root.findall(f".//{{{DS_NS}}}Reference")
        assert len(references) == 2

        first, second = (resolve_reference("", ref) for ref in references)

        assert b"SECOND" in first and b"FIRST" not in first
        assert b"FIRST" in second and b"SECOND" not in second
        assert first != second
        assert b"<Amount>100</Amount>" in first

    def test_detached_reference_still_strips_every_signature(self):
        doc = f'<Invoice xmlns:ds="{DS_NS}"><A/><ds:Signature Id="s"/></Invoice>'
        root = etree.fromstring(doc.encode())
        reference = etree.SubElement(root, f"{{{DS_NS}}}Reference")
        assert b"Signature" not in resolve_reference("", reference)

    def test_signature_tail_is_preserved(self):
        doc = f'<Invoice xmlns:ds="{DS_NS}"><A/><ds:Signature/>TAIL</Invoice>'
        root = etree.fromstring(doc.encode())
        octets = resolve_reference("", root.find(f"{{{DS_NS}}}Signature"))
        assert b"TAIL" in octets

    def test_tail_folds_into_parent_when_signature_is_first(self):
        doc = f'<Invoice xmlns:ds="{DS_NS}"><ds:Signature/>TAIL<A/></Invoice>'
        root = etree.fromstring(doc.encode())
        octets = resolve_reference("", root.find(f"{{{DS_NS}}}Signature"))
        assert b"TAIL" in octets

    def test_diverges_from_legacy_regex_on_leading_whitespace(self):
        root = _tree()
        legacy = canonicalize(
            re.sub(
                r"^[^\n]*<ds:Signature.*<\/ds:Signature>",
                r"",
                etree.tostring(root.getroottree(), encoding="unicode"),
                flags=re.DOTALL | re.MULTILINE,
            )
        )
        current = resolve_reference("", _first_reference(root))
        assert current != legacy
        assert current.replace(b"\n  \n", b"\n\n") == legacy


class TestSameDocumentReference:
    def test_resolves_id_attribute(self):
        root = _tree()
        octets = resolve_reference("#line-1", _first_reference(root))
        assert b"<Amount>100</Amount>" in octets
        assert b"Invoice" not in octets

    def test_id_match_is_case_sensitive(self):
        doc = '<Invoice><Line id="x"/></Invoice>'
        root = etree.fromstring(doc.encode())
        with pytest.raises(XmlSigError, match="not found"):
            resolve_reference("#x", root.find("Line"))

    def test_ambiguous_reference_is_rejected(self):
        doc = '<Invoice><A Id="dup"/><B Id="dup"/></Invoice>'
        root = etree.fromstring(doc.encode())
        with pytest.raises(XmlSigError, match="Ambiguous"):
            resolve_reference("#dup", root.find("A"))

    def test_unknown_uri_is_rejected(self):
        root = _tree()
        with pytest.raises(XmlSigError, match="not found"):
            resolve_reference("#nope", _first_reference(root))


class TestCanonicalizationMode:
    def test_inclusive_when_no_exclusive_transform(self):
        root = _tree()
        octets = resolve_reference("#line-1", _first_reference(root))
        assert b"xmlns:ds" in octets

    def test_exclusive_when_transform_says_so(self):
        doc = f"""<Invoice xmlns:ds="{DS_NS}">
          <Line Id="line-1"><Amount>100</Amount></Line>
          <ds:Reference URI="#line-1">
            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
          </ds:Reference>
        </Invoice>"""
        root = etree.fromstring(doc.encode())
        reference = root.find(f"{{{DS_NS}}}Reference")
        octets = resolve_reference("#line-1", reference)
        assert b"xmlns:ds" not in octets


class TestSignedInfoCanonicalization:
    def test_inclusive_by_default(self):
        doc = f"""<ds:SignedInfo xmlns:ds="{DS_NS}" xmlns:x="urn:x">
          <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
        </ds:SignedInfo>"""
        octets = canonicalize_signed_info(etree.fromstring(doc.encode()))
        assert b'xmlns:x="urn:x"' in octets

    def test_exclusive_when_method_says_so(self):
        doc = f"""<ds:SignedInfo xmlns:ds="{DS_NS}" xmlns:x="urn:x">
          <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
        </ds:SignedInfo>"""
        octets = canonicalize_signed_info(etree.fromstring(doc.encode()))
        assert b'xmlns:x="urn:x"' not in octets

    def test_prefix_list_is_kept_inclusive(self):
        doc = f"""<ds:SignedInfo xmlns:ds="{DS_NS}" xmlns:x="urn:x">
          <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
            <ec:InclusiveNamespaces xmlns:ec="urn:ec" PrefixList="x"/>
          </ds:CanonicalizationMethod>
        </ds:SignedInfo>"""
        octets = canonicalize_signed_info(etree.fromstring(doc.encode()))
        assert b'xmlns:x="urn:x"' in octets

    def test_reference_transforms_do_not_affect_signed_info(self):
        doc = f"""<ds:SignedInfo xmlns:ds="{DS_NS}" xmlns:x="urn:x">
          <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
          <ds:Reference URI="">
            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
          </ds:Reference>
        </ds:SignedInfo>"""
        octets = canonicalize_signed_info(etree.fromstring(doc.encode()))
        assert b'xmlns:x="urn:x"' in octets


class TestDigests:
    @pytest.mark.parametrize("algorithm", ["sha1", "sha256"])
    def test_digest_algorithm_is_honoured(self, algorithm):
        root = _tree()
        signed_info = _signed_info(root)
        update_reference_digests(signed_info, algorithm=algorithm)
        reference = _first_reference(root)
        octets = resolve_reference("", reference)
        expected = b64encode(hashlib.new(algorithm, octets).digest())
        assert reference.find(f"{{{DS_NS}}}DigestValue").text == expected.decode()

    def test_every_reference_is_filled(self):
        root = _tree()
        signed_info = _signed_info(root)
        update_reference_digests(signed_info)
        values = [e.text for e in signed_info.iter(f"{{{DS_NS}}}DigestValue")]
        assert len(values) == 2
        assert all(values)


class TestReferenceCost:
    def test_an_id_reference_reads_the_document_without_copying_it(self, monkeypatch):
        def refuse(_node):
            raise AssertionError("an #id reference copied the document")

        monkeypatch.setattr("odoo.libs.xml.dsig.deepcopy", refuse)
        octets = resolve_reference("#line-1", _first_reference(_tree()))
        assert b"<Amount>100</Amount>" in octets

    def test_a_prefix_list_with_repeated_spaces_names_no_empty_prefix(
        self, monkeypatch
    ):
        doc = f"""<ds:SignedInfo xmlns:ds="{DS_NS}" xmlns:x="urn:x">
          <ds:CanonicalizationMethod Algorithm="{EXC_C14N_ALGORITHM}">
            <ec:InclusiveNamespaces xmlns:ec="{EXC_C14N_ALGORITHM}"
                PrefixList="x   ds "/>
          </ds:CanonicalizationMethod>
        </ds:SignedInfo>"""
        seen = []
        monkeypatch.setattr(
            "odoo.libs.xml.dsig.canonicalize",
            lambda node, **kw: seen.append(kw["inclusive_ns_prefixes"]) or b"",
        )
        canonicalize_signed_info(etree.fromstring(doc.encode()))
        assert seen == [["x", "ds"]]
