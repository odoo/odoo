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
            for lines_chunk in map(self.env['pos.order.line'].sudo().browse, split_every(100000, lines.ids)):
                if any(tid in self_ids for ts in lines_chunk.read(['tax_ids']) for tid in ts['tax_ids']):
                    raise UserError(_(
                        'It is forbidden to modify a tax used in a POS order not posted. '
                        'You must close the POS sessions before modifying the tax.'
                    ))
                lines_chunk.invalidate_recordset(['tax_ids'])
        return super(AccountTax, self).write(vals)

    def _hook_compute_is_used(self, taxes_to_compute):
        # OVERRIDE in order to fetch taxes used in pos

        used_taxes = super()._hook_compute_is_used(taxes_to_compute)
        taxes_to_compute -= used_taxes

        if taxes_to_compute:
            self.env['pos.order.line'].flush_model(['tax_ids'])
            self.env.cr.execute("""
                SELECT id
                FROM account_tax
                WHERE EXISTS(
                    SELECT 1
                    FROM account_tax_pos_order_line_rel AS pos
                    WHERE account_tax_id IN %s
                    AND account_tax.id = pos.account_tax_id
                )
            """, [tuple(taxes_to_compute)])

            used_taxes.update([tax[0] for tax in self.env.cr.fetchall()])

        return used_taxes
