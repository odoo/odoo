# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import re
from base64 import b64encode

from lxml import etree
from odoo.tools.xml_utils import cleanup_xml_node


# Utility Methods for Basque Country's TicketBAI XML-related stuff.

NS_MAP = {'': 'http://www.w3.org/2000/09/xmldsig#'}  # default namespace matches signature's `ds:``


def canonicalize_node(node):
    """
    Returns the canonical (C14N 1.0, without comments, non exclusive) representation of node.
    Speficied in: https://www.w3.org/TR/2001/REC-xml-c14n-20010315
    Required for computing digests and signatures.
    Returns an UTF-8 encoded bytes string.
    """
    node = etree.fromstring(node) if isinstance(node, str) else node
    return etree.tostring(node, method='c14n', with_comments=False, exclusive=False)


def cleanup_xml_signature(xml_sig):
    """
    Cleanups the content of the provided string representation of an XML signature.
    In addition, removes all line feeds for the ds:Object element.
    Turns self-closing tags into regular tags (with an empty string content)
    as the former may not be supported by some signature validation implementations.
    Returns an etree._Element
    """
    sig_elem = cleanup_xml_node(xml_sig, remove_blank_nodes=False, indent_level=-1)
    etree.indent(sig_elem, space='')  # removes indentation
    for elem in sig_elem.find('Object', namespaces=NS_MAP).iter():
        if elem.text == '\n':
            elem.text = ''  # keeps the signature in one line, prevents self-closing tags
        elem.tail = ''  # removes line feed and whitespace after the tag
    return sig_elem


def get_uri(uri, reference, base_uri):
    """
    Returns the content within `reference` that is identified by `uri`.
    Canonicalization is used to convert node reference to an octet stream.
    - The base_uri points to the whole document tree, without the signature
    https://www.w3.org/TR/xmldsig-core/#sec-EnvelopedSignature

    - URIs starting with # are same-document references
    https://www.w3.org/TR/xmldsig-core/#sec-URI

    Returns an UTF-8 encoded bytes string.
    """
    node = reference.getroottree()
    if uri == base_uri:
        # Empty URI: whole document, without signature
        return canonicalize_node(
            re.sub(
                r'^[^\n]*<ds:Signature.*<\/ds:Signature>', r'',
                etree.tostring(node, encoding='unicode'),
                flags=re.DOTALL | re.MULTILINE)
        )

    if uri.startswith('#'):
        query = '//*[@*[local-name() = "Id" ]=$uri]'  # case-sensitive 'Id'
        results = node.xpath(query, uri=uri.lstrip('#'))
        if len(results) == 1:
            return canonicalize_node(results[0])
        if len(results) > 1:
            raise Exception("Ambiguous reference URI {} resolved to {} nodes".format(
                uri, len(results)))

    raise Exception(f"URI {uri!r} not found")


def calculate_references_digests(node, base_uri=''):
    """
    Processes the references from node and computes their digest values as specified in
    https://www.w3.org/TR/xmldsig-core/#sec-DigestMethod
    https://www.w3.org/TR/xmldsig-core/#sec-DigestValue
    """
    for reference in node.findall('Reference', namespaces=NS_MAP):
        ref_node = get_uri(reference.get('URI', ''), reference, base_uri)
        hash_digest = hashlib.new('sha256', ref_node).digest()
        reference.find('DigestValue', namespaces=NS_MAP).text = b64encode(hash_digest)
