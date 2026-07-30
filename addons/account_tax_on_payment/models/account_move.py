# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    advanced_payment_tax_origin_move_id = fields.Many2one('account.move', string="Advanced payment tax origin move")
    advanced_payment_tax_created_move_ids = fields.One2many('account.move', 'advanced_payment_tax_origin_move_id', string="Advanced payment tax created moves")
    tax_advanced_adjust_rec_id = fields.Many2one('account.partial.reconcile', string="Tax Advance Adjust")

    def open_advanced_payment_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Advanced Payment Tax Entries"),
            'res_model': 'account.move',
            'view_mode': 'form',
            'domain': [('id', 'in', self.advanced_payment_tax_created_move_ids.ids)],
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
        }

    def button_draft(self):
        res = super().button_draft()
        for move in self:
            if move.advanced_payment_tax_origin_move_id:
                # don't want to allow setting the Advanced Payment Tax entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                raise UserError(_('You cannot reset to draft a Advanced Payment Tax journal entry.'))
        return res

    def _post(self, soft=True):
        res = super()._post(soft)
        for payment_move in self.filtered(lambda m: m.payment_id and m.payment_id.tax_ids):
            reduced_liquidity_lines = payment_move.line_ids.filtered(lambda l: l.account_id == payment_move.payment_id.outstanding_account_id)
            if len(reduced_liquidity_lines) > 1:
                reduced_liquidity_lines.reconcile()
            reduced_counterpart_lines = payment_move.line_ids.filtered(lambda l: l.account_id == payment_move.payment_id.destination_account_id)
            if len(reduced_counterpart_lines) > 1:
                reduced_counterpart_lines.reconcile()
        return res
