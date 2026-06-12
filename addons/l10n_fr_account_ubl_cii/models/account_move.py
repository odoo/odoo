from odoo import api, models
from odoo.tools import html2plaintext

from odoo.addons.l10n_fr_account_ubl_cii.models.account_edi_xml_ubl_21_fr import PDP_CUSTOMIZATION_ID


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_fr_get_default_notes(self):
        self.ensure_one()
        # Mandatory / default notes for French e-invoicing [BR-FR-05]
        # Only add them when company if France
        if not self.company_id.is_france_country:
            return {}
        payment_term = self.invoice_payment_term_id
        return {
            'PMT': self.env._("In the event of late payment, a flat-rate fee of €40 for collection costs will be charged (Articles L.441-10 and D.441-5 of the Code de commerce)."),
            'PMD': self.env._("Late payment penalties at an annual rate of 10% are applied if the payment is made after the due date."),
            'AAB': html2plaintext(payment_term.note) if payment_term.early_discount else self.env._("No discount for early payment."),
        }

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        # Extends account_edi_ubl_cii
        customization_id = tree.find('{*}CustomizationID')
        # Note: The CustomizationID alone is not enough because e.g. SuperPDP just sends `urn:cen.eu:en16931:2017`
        #       but still expects the full French validation.
        if customization_id is not None and customization_id.text == PDP_CUSTOMIZATION_ID:
            receiver_endpoint_node = tree.find('./{*}AccountingCustomerParty/{*}Party/{*}EndpointID')
            if receiver_endpoint_node is not None and receiver_endpoint_node.get('schemeID') == '0225':
                return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)
