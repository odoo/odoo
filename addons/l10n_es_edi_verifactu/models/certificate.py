from odoo import fields, models
from cryptography import x509
import base64


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('verifactu', 'Veri*Factu'),
        ],
    )

    def _l10n_es_edi_verifactu_is_sello_certificate(self):
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.with_context(bin_size=False).pem_certificate))
        subject = cert.subject
        given_names = subject.get_attributes_for_oid(x509.NameOID.GIVEN_NAME)
        if given_names:
            return False
        organization_identifier_oid = x509.ObjectIdentifier('2.5.4.97')
        org_id_attrs = subject.get_attributes_for_oid(organization_identifier_oid)
        return bool(org_id_attrs and org_id_attrs[0].value.startswith('VATES-'))
