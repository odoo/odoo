from odoo import models


class AccountEdiXmlUBLEN16931Extended(models.AbstractModel):
    _name = "account.edi.xml.ubl_en16931_extended"
    _inherit = "account.edi.xml.ubl_en16931"
    _description = "UBL EN16931 France CIUS Extended"

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'CreditNoteLineType_template': 'l10n_fr_pdp.ubl_en16931_extended_CreditNoteLineType',
            'DebitNoteLineType_template': 'l10n_fr_pdp.ubl_en16931_extended_DebitNoteLineType',
            'PaymentMeansType_template': 'l10n_fr_pdp.ubl_en16931_extended_PaymentMeansType',
            'PartyType_template': 'l10n_fr_pdp.ubl_en16931_extended_PartyType',
            'DeliveryType_template': 'l10n_fr_pdp.ubl_en16931_extended_DeliveryType',
            'AgentParty_template': 'l10n_fr_pdp.ubl_en16931_extended_agent_party',

            # Not sure for those three ?
            'InvoiceType_template': 'l10n_fr_pdp.ubl_en16931_extended_common_type',
            'CreditNoteType_template': 'l10n_fr_pdp.ubl_en16931_extended_common_type',
            'DebitNoteType_template': 'l10n_fr_pdp.ubl_en16931_extended_common_type',
        })

        return vals
