from base64 import b64decode, b64encode, encodebytes
from copy import deepcopy
from hashlib import sha1

from cryptography.hazmat.primitives import hashes, serialization
from lxml import etree

from odoo import _, api, fields, models
from odoo.addons.account.tools.certificate import load_key_and_certificates
from odoo.addons.l10n_es_edi_facturae import xml_utils
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node

class Certificate(models.Model):
    _name = 'l10n_es_edi_facturae.certificate'
    _description = 'Facturae Digital Certificate'
    _order = 'date_start desc, id desc'
    _rec_name = 'serial_number'

    content = fields.Binary(string="PFX Certificate", required=True, help="PFX Certificate")
    password = fields.Char(help="Passphrase for the PFX certificate")
    serial_number = fields.Char(readonly=True, index=True, help="The serial number to add to electronic documents")
    date_start = fields.Datetime(readonly=True, help="The date on which the certificate starts to be valid")
    date_end = fields.Datetime(readonly=True, help="The date on which the certificate expires")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company, required=True, readonly=True)

    def _decode_certificate(self):
        """
        Return certificate data

        :return tuple: private_key, certificate
        """
        self.ensure_one()
        content, password = b64decode(self.with_context(bin_size=False).content), self.password.encode() if self.password else None
        return load_key_and_certificates(content, password)

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        certificates = super().create(vals_list)
        for certificate in certificates:
            try:
                _key, certif = certificate._decode_certificate()
            except ValueError:
                raise UserError(_('There has been a problem with the certificate, some usual problems can be:\n'
                                  '\t- The password given or the certificate are not valid.\n'
                                  '\t- The certificate content is invalid.'))
            if fields.datetime.now() > certif.not_valid_after:
                raise UserError(_('The certificate is expired since %s', certif.not_valid_after))
            # Assign extracted values from the certificate
            certificate.write({'serial_number': certif.serial_number, 'date_start': certif.not_valid_before, 'date_end': certif.not_valid_after})
        return certificates

    # -------------------------------------------------------------------------
    # BUSINESS METHODS                                                        #
    # -------------------------------------------------------------------------
    def _sign_xml(self, edi_data, signature_data):
        """
        Signs the given XML data with the certificate and private key.

        :param etree._Element edi_data: The XML data to sign.
        :param dict signature_data: The signature data to use.
        :return: The signed XML data string.
        :rtype: str
        """
        self.ensure_one()
        if not (self.date_start < fields.Datetime.now() < self.date_end):
            raise UserError('Facturae certificate date is not valid, its validity has probably expired')
        root = deepcopy(edi_data)
        cert_private, cert_public = self._decode_certificate()
        public_key_numbers = cert_public.public_key().public_numbers()

        rfc4514_attr = dict(element.rfc4514_string().split("=", 1) for element in cert_public.issuer.rdns)

        # The 'Organizational Unit' field is optional
        issuer = f"CN={rfc4514_attr.pop('CN')}, "
        if 'OU' in rfc4514_attr:
            issuer += f"OU={rfc4514_attr.pop('OU')}, "
        issuer += f"O={rfc4514_attr.pop('O')}, C={rfc4514_attr.pop('C')}"

        # Add remaining certificate fields (not all certificates have other fields)
        issuer += "".join([f", {key}={value}" for key, value in rfc4514_attr.items()])

        # Identifiers
        document_id = f"Document-{sha1(etree.tostring(edi_data)).hexdigest()}"
        signature_id = f"Signature-{document_id}"
        keyinfo_id = f"KeyInfo-{document_id}"
        sigproperties_id = f"SignatureProperties-{document_id}"

        signature_data.update({
            'document_id': document_id,
            'x509_certificate': encodebytes(cert_public.public_bytes(encoding=serialization.Encoding.DER)).decode(),
            'public_modulus': encodebytes(xml_utils._int_to_bytes(public_key_numbers.n)).decode(),
            'public_exponent': encodebytes(xml_utils._int_to_bytes(public_key_numbers.e)).decode(),
            'iso_now': fields.datetime.now().isoformat(),
            'keyinfo_id': keyinfo_id,
            'signature_id': signature_id,
            'sigproperties_id': sigproperties_id,
            'reference_uri': "Reference-" + document_id,
            'sigpolicy_url': "http://www.facturae.es/politica_de_firma_formato_facturae/politica_de_firma_formato_facturae_v3_1.pdf",
            'sigpolicy_description': "Política de firma electrónica para facturación electrónica con formato Facturae",
            'sigcertif_digest': b64encode(cert_public.fingerprint(hashes.SHA256())).decode(),
            'x509_issuer_description': issuer,
            'x509_serial_number': cert_public.serial_number,
        })
        signature = self.env['ir.qweb']._render('l10n_es_edi_facturae.template_xades_signature', signature_data)
        signature = cleanup_xml_node(signature, remove_blank_nodes=False)
        root.append(signature)
        xml_utils._reference_digests(signature.find("ds:SignedInfo", namespaces=xml_utils.NS_MAP))
        xml_utils._fill_signature(signature, cert_private)

        return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
