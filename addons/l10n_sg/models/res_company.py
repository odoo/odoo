# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company']

    l10n_sg_unique_entity_number = fields.Char(string='UEN', related="partner_id.l10n_sg_unique_entity_number", readonly=False)

    def _peppol_modules_document_types(self):
        document_types = super()._peppol_modules_document_types()
        document_types['l10n_sg'] = {
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0::2.1":
                "Billing International Singapore 3.0 Invoice",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0::2.1":
                "Billing International Singapore 3.0 CreditNote",
        }
        return document_types
