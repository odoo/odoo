from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _l10n_in_edi_generate_invoice_json(self, invoice):
        generate_json = super()._l10n_in_edi_generate_invoice_json(invoice)
        if invoice.move_type != 'out_refund' and invoice.debit_origin_id:
            generate_json['DocDtls']['Typ'] = 'DBN'
        return generate_json
