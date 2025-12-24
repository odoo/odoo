from odoo import models


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_ro"

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        vals['commodity_classification_vals'] = [{
            'item_classification_code': line.product_id.cpv_code_id.code,
            'item_classification_attrs': {'listID': 'CPV'},
        }]
        return vals
