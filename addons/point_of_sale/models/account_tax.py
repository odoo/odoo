# -*- coding: utf-8 -*-

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def write(self, vals):
        forbidden_fields = set([
            'amount_type', 'amount', 'type_tax_use', 'tax_group_id', 'price_include',
            'include_base_amount', 'is_base_affected',
        ])
        if forbidden_fields & set(vals.keys()):
            open_lines = self.env['pos.order.line'].sudo().search([
                ('order_id.session_id.state', '!=', 'closed')
            ])
            if not set(self.ids).isdisjoint(open_lines.tax_ids.ids):
                raise UserError(_(
                    'It is forbidden to modify a tax used in a POS order not posted. '
                    'You must close the POS sessions before modifying the tax.'
                ))
        return super(AccountTax, self).write(vals)
