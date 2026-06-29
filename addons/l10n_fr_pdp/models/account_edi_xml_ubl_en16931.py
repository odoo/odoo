from odoo import models

note = {
  "AAB": "Cash Discount Mention",
  "AAI": "General Information: elements usually in the footer of paper invoices.",
  "ABL": "Legal Information: e.g., trade registry number, Company Registration Number (RCS).",
  "ACC": "Factoring Subrogation Clause.",
  "BLU": "Eco-participation",
  "DCL": "Invoice Creator's Declaration (in case of billing mandate): 'invoice issued by A on behalf of B'.",
  "PMT": "Mention of the fixed 40€ recovery compensation fee.",
  "PMD": "Late Payment Penalties Mention.",
  "SUR": "Supplier Remarks.",
  "TXD": "Mention of Single Taxable Person Member."
}


class AccountEdiXmlUBLEN16931(models.AbstractModel):
    _name = "account.edi.xml.ubl_en16931"
    _inherit = "account.edi.xml.ubl_21"
    _description = "UBL EN16931 France CIUS"

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'CreditNoteLineType_template': 'l10n_fr_pdp.ubl_en16931_CreditNoteLineType',
            'DebitNoteLineType_template': 'l10n_fr_pdp.ubl_en16931_DebitNoteLineType',
            'PaymentMeansType_template': 'l10n_fr_pdp.ubl_en16931_PaymentMeansType',
            'AddressType_template': 'l10n_fr_pdp.ubl_en16931_AddressType',
            'PartyType_template': 'l10n_fr_pdp.ubl_en16931_PartyType',
            # Not sure for those three ?
            'InvoiceType_template': 'l10n_fr_pdp.ubl_en16931_common_type',
            'CreditNoteType_template': 'l10n_fr_pdp.ubl_en16931_common_type',
            'DebitNoteType_template': 'l10n_fr_pdp.ubl_en16931_common_type',
        })

        return vals
