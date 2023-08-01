# -*- coding: utf-8 -*-

from collections import Counter
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
                lines_chunk.invalidate_recordset(['tax_ids'])
        return super(AccountTax, self).write(vals)

    def _hook_compute_is_used(self):
        # OVERRIDE in order to count the usage of taxes in pos order lines

        taxes_in_transactions_ctr = Counter(dict(self.env['pos.order.line']._read_group([], groupby=['tax_ids'], aggregates=['__count'])))

        return super()._hook_compute_is_used() + taxes_in_transactions_ctr
