from lxml import etree
import requests

from base64 import b64encode
from copy import deepcopy
from datetime import timedelta
import hashlib
import logging
import uuid

from odoo.exceptions import UserError, ValidationError
from odoo import fields, _

_logger = logging.getLogger(__name__)


NS_MAP = {'ds': "http://www.w3.org/2000/09/xmldsig#"}

TEST_ENDPOINT = "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl"
ENDPOINT = "https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl"

FORCED_PROD_SERVICES = {'GetAcquirer'}


def _canonicalize_node(node, **kwargs):
    """
    Returns the canonical representation of node.
    Specified in: https://www.w3.org/TR/2001/REC-xml-c14n-20010315
    Required for computing digests and signatures.
    Returns an UTF-8 encoded bytes string.
    """
    return etree.tostring(node, method="c14n", with_comments=False, **kwargs)


def _get_uri(uri, reference, base_uri=""):
    """
    Returns the content within `reference` that is identified by `uri`.
    Canonicalization is used to convert node reference to an octet stream.
    - URIs starting with # are same-document references
    https://www.w3.org/TR/xmldsig-core/#sec-URI
    - Empty URIs point to the whole document tree, without the signature
    https://www.w3.org/TR/xmldsig-core/#sec-EnvelopedSignature
    Returns an UTF-8 encoded bytes string.
    """
    transform_nodes = reference.findall(".//{*}Transform")
    # handle exclusive canonization
    exc_c14n = bool(transform_nodes) and transform_nodes[0].attrib.get('Algorithm') == 'http://www.w3.org/2001/10/xml-exc-c14n#'
    prefix_list = []
    if exc_c14n:
        inclusive_ns_node = transform_nodes[0].find(".//{*}InclusiveNamespaces")
        if inclusive_ns_node is not None and inclusive_ns_node.attrib.get('PrefixList'):
            prefix_list = inclusive_ns_node.attrib.get('PrefixList').split(' ')

    node = deepcopy(reference.getroottree().getroot())
    if uri == base_uri:
        # Base URI: whole document, without signature (default is empty URI)
        for signature in node.findall('.//ds:Signature', namespaces=NS_MAP):
            if signature.tail:
                # move the tail to the previous node or to the parent
                if (previous := signature.getprevious()) is not None:
                    previous.tail = "".join([previous.tail or "", signature.tail or ""])
                else:
                    signature.getparent().text = "".join([signature.getparent().text or "", signature.tail or ""])
            signature.getparent().remove(signature)  # we can only remove a node from its direct parent
        return _canonicalize_node(node, exclusive=exc_c14n, inclusive_ns_prefixes=prefix_list)

    if uri.startswith("#"):
        path = "//*[@*[local-name() = '{}' ]=$uri]"
        results = node.xpath(path.format("Id"), uri=uri.lstrip("#"))  # case-sensitive 'Id'
        if len(results) == 1:
            return _canonicalize_node(results[0], exclusive=exc_c14n, inclusive_ns_prefixes=prefix_list)
        if len(results) > 1:
            raise UserError(f"Ambiguous reference URI {uri} resolved to {len(results)} nodes")

    raise UserError(f'URI {uri} not found')


def _reference_digests(node, base_uri=""):
    """
    Processes the references from node and computes their digest values as specified in
    https://www.w3.org/TR/xmldsig-core/#sec-DigestMethod
    https://www.w3.org/TR/xmldsig-core/#sec-DigestValue
    """
    for reference in node.findall("ds:Reference", namespaces=NS_MAP):
        ref_node = _get_uri(reference.get("URI", ""), reference, base_uri=base_uri)
        lib = hashlib.new("sha256", ref_node)
        reference.find("ds:DigestValue", namespaces=NS_MAP).text = b64encode(lib.digest())


def _fill_signature(node, certificate):
    """
    Uses certificate to sign the SignedInfo sub-node of `node`, as specified in:
    https://www.w3.org/TR/xmldsig-core/#sec-SignatureValue
    https://www.w3.org/TR/xmldsig-core/#sec-SignedInfo
    """
    signed_info_xml = node.find("ds:SignedInfo", namespaces=NS_MAP)

    exc_c14n = signed_info_xml.find(".//{*}CanonicalizationMethod").attrib.get('Algorithm') == 'http://www.w3.org/2001/10/xml-exc-c14n#'
    prefix_list = []
    if exc_c14n:
        inclusive_ns_node = signed_info_xml.find(".//{*}CanonicalizationMethod").find(".//{*}InclusiveNamespaces")
        if inclusive_ns_node is not None and inclusive_ns_node.attrib.get('PrefixList'):
            prefix_list = inclusive_ns_node.attrib.get('PrefixList').split(' ')

    signature = certificate._sign(
        _canonicalize_node(signed_info_xml, exclusive=exc_c14n, inclusive_ns_prefixes=prefix_list),
    )
    node.find("ds:SignatureValue", namespaces=NS_MAP).text = signature.decode()


def _remove_tail_and_text_in_hierarchy(node):
    """ Recursively remove the tail of all nodes in hierarchy and remove the text of all non-leaf nodes. """
    node.tail = None
    if list(node):
        node.text = None
        for child in node:
            _remove_tail_and_text_in_hierarchy(child)


def _uuid1():
    return uuid.uuid1()


def _build_and_send_request(self, payload, service, company):
    cert_sudo = company.sudo().l10n_co_dian_certificate_ids[-1:]
    if not cert_sudo:
        raise ValidationError(_('Certificate is not available'))
    dt_now = fields.datetime.utcnow()
    vals = {
        'creation_time': dt_now.isoformat(timespec='milliseconds') + "Z",
        'expiration_time': (dt_now + timedelta(seconds=60000)).isoformat(timespec='milliseconds') + "Z",
        'binary_security_token_id': "X509-" + str(_uuid1()),
        'binary_security_token': cert_sudo._get_der_certificate_bytes(formatting='base64').decode(),
        'wsa_node_id': "id-" + str(_uuid1()),
        'action': f"http://wcf.dian.colombia/IWcfDianCustomerServices/{service}",
        **payload,
    }
    envelope = etree.fromstring(self.env['ir.qweb']._render('l10n_co_dian.soap_request_dian', vals))
    _remove_tail_and_text_in_hierarchy(envelope)
    # Hash and sign
    _reference_digests(envelope.find(".//ds:SignedInfo", {'ds': 'http://www.w3.org/2000/09/xmldsig#'}))
    _fill_signature(envelope.find(".//ds:Signature", {'ds': 'http://www.w3.org/2000/09/xmldsig#'}), cert_sudo)
    # Send the request
    try:
        response = requests.post(
            url=TEST_ENDPOINT if company.l10n_co_dian_test_environment and service not in FORCED_PROD_SERVICES else ENDPOINT,
            data=etree.tostring(envelope),
            timeout=3,
            headers={"Content-Type": f'application/soap+xml;charset=UTF-8;action="http://wcf.dian.colombia/IWcfDianCustomerServices/{service}"'},
        )
    except requests.exceptions.ReadTimeout:
        return {'response': '', 'status_code': ''}
    if response.status_code != 200:
        _logger.info("DIAN server returned code %s\n%s", response.status_code, response.text)
    return {'response': response.text, 'status_code': response.status_code}


def _get_qr_code_value(root, currency, is_support_document=False):
    """ Returns the value to be embedded inside the QR Code on the PDF report.
    For Support Documents, see section 12.2 ('Anexo-Tecnico-Documento-Soporte[...].pdf').
    Otherwise, see section 11.7 ('Anexo-Tecnico-[...]-1-9.pdf').
    """
    nsmap = {k: v for k, v in root.nsmap.items() if k}  # empty namespace prefix is not supported for XPaths
    supplier_company_id = root.findtext('./cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID', namespaces=nsmap)
    customer_company_id = root.findtext('./cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID', namespaces=nsmap)
    line_extension_amount = root.findtext('./cac:LegalMonetaryTotal/cbc:LineExtensionAmount', namespaces=nsmap)
    tax_amount_01 = currency.round(sum(float(x) for x in root.xpath('./cac:TaxTotal[.//cbc:ID/text()="01"]/cbc:TaxAmount/text()', namespaces=nsmap)))
    payable_amount = root.findtext('./cac:LegalMonetaryTotal/cbc:PayableAmount', namespaces=nsmap)
    identifier = root.findtext('./cbc:UUID', namespaces=nsmap)
    qr_code = root.findtext('./ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sts:DianExtensions/sts:QRCode', namespaces=nsmap)
    vals = {
        'NumDS': root.findtext('./cbc:ID', namespaces=nsmap),
        'FecFD': root.findtext('./cbc:IssueDate', namespaces=nsmap),
        'HorDS': root.findtext('./cbc:IssueTime', namespaces=nsmap),
    }
    if is_support_document:
        vals.update({
            'NumSNO': supplier_company_id,
            'DocABS': customer_company_id,
            'ValDS': line_extension_amount,
            'ValIva': tax_amount_01,
            'ValTolDS': payable_amount,
            'CUDS': identifier,
            'QRCode': qr_code,
        })
    else:
        vals.update({
            'NitFac': supplier_company_id,
            'DocAdq': customer_company_id,
            'ValFac': line_extension_amount,
            'ValIva': tax_amount_01,
            'ValOtroIm': currency.round(sum(float(x) for x in root.xpath('./cac:TaxTotal[.//cbc:ID/text()!="01"]/cbc:TaxAmount/text()', namespaces=nsmap))),
            'ValTolFac': payable_amount,
            'CUFE': identifier,
            'QRCode': qr_code,
        })
    return "\n".join(f"{k}: {v}" for k, v in vals.items())
