from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ae_registration_identifier = fields.Char(related='partner_id.l10n_ae_registration_identifier', readonly=False)
    l10n_ae_registration_identifier_type = fields.Selection(related='partner_id.l10n_ae_registration_identifier_type', readonly=False)
    l10n_ae_authority_name = fields.Char(related='partner_id.l10n_ae_authority_name', readonly=False)
    l10n_ae_passport_issuing_country_id = fields.Many2one(related='partner_id.l10n_ae_passport_issuing_country_id', readonly=False)

    def _peppol_modules_document_types(self):
        # EXTENDS account_peppol
        document_types = super()._peppol_modules_document_types()
        document_types['l10n_ae_ubl_pint'] = {
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:billing-1@ae-1::2.1":
                "PINT AE UBL Invoice",
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:billing-1@ae-1*::2.1":
                "PINT AE UBL Invoice (Wildcard)",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:billing-1@ae-1::2.1":
                "PINT AE UBL CreditNote",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:billing-1@ae-1*::2.1":
                "PINT AE UBL CreditNote (Wildcard)",
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:selfbilling-1@ae-1::2.1":
                "PINT AE UBL Self-Billing Invoice",
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:selfbilling-1@ae-1*::2.1":
                "PINT AE UBL Self-Billing Invoice (Wildcard)",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:selfbilling-1@ae-1::2.1":
                "PINT AE UBL Self-Billing CreditNote",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:selfbilling-1@ae-1*::2.1":
                "PINT AE UBL Self-Billing CreditNote (Wildcard)",
        }
        return document_types
