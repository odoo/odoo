from odoo import models, api
from collections import OrderedDict

class AccountInvoiceLine(models.Model):

    _inherit = 'account.invoice.line'

    def _get_onchange_create(self):
        return OrderedDict([
            ('_onchange_product_id', ['account_id', 'name', 'price_unit', 'uom_id', 'invoice_line_tax_ids']),
        ])

    @api.model_create_multi
    def create(self, vals_list):

        onchanges = self._get_onchange_create()
        for onchange_method, changed_fields in onchanges.items():
            for vals in vals_list:
                if any(f not in vals for f in changed_fields):
                    line = self.new(vals)
                    getattr(line, onchange_method)()
                    for field in changed_fields:
                        if field not in vals and line[field]:
                            vals[field] = line._fields[field].convert_to_write(line[field], line)

        return super().create(vals_list)
