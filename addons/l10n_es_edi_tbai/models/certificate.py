import base64

from cryptography import x509

from odoo import fields, models


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('tbai', 'TBAI')
        ],
    )

    def _l10n_es_edi_tbai_get_issuer(self):
        self.ensure_one()

        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))

        common_name = cert.issuer.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
        org_unit = cert.issuer.get_attributes_for_oid(x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
        org_name = cert.issuer.get_attributes_for_oid(x509.oid.NameOID.ORGANIZATION_NAME)[0].value
        country_name = cert.issuer.get_attributes_for_oid(x509.oid.NameOID.COUNTRY_NAME)[0].value

        return f'CN={common_name}, OU={org_unit}, O={org_name}, C={country_name}'
