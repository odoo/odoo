# -*- coding: utf-8 -*-

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import split_every


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def write(self, vals):
        forbidden_fields = {
            'amount_type', 'amount', 'type_tax_use', 'tax_group_id', 'price_include',
            'include_base_amount', 'is_base_affected',
        }
        if forbidden_fields & set(vals.keys()):
            lines = self.env['pos.order.line'].sudo().search([
                ('order_id.session_id.state', '!=', 'closed')
            ])
            self_ids = set(self.ids)
            for lines_chunk in map(self.env['pos.order.line'].browse, split_every(100000, lines.ids)):
                if any(tid in self_ids for ts in lines_chunk.read(['tax_ids']) for tid in ts['tax_ids']):
                    raise UserError(_(
                        'It is forbidden to modify a tax used in a POS order not posted. '
                        'You must close the POS sessions before modifying the tax.'
                    ))
                lines_chunk.invalidate_cache(['tax_ids'], lines_chunk.ids)
        return super(AccountTax, self).write(vals)

    def get_real_tax_amount(self):
        tax_list = []
        for tax in self:
            tax_repartition_lines = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
            total_factor = sum(tax_repartition_lines.mapped('factor'))
            real_amount = tax.amount * total_factor
            tax_list.append({'id': tax.id, 'amount': real_amount})
        return tax_list
