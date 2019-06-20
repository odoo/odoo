# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_in_unit_id = fields.Many2one('res.partner', string="Operating Unit", ondelete="restrict",
        default=lambda self: self.env.user._get_default_unit())
    show_l10n_in_unit_id_field = fields.Boolean(compute='_compute_show_l10n_in_unit_id_field')

    @api.depends('invoice_ids')
    def _compute_show_l10n_in_unit_id_field(self):
        for record in self:
            if len(record.invoice_ids.mapped('l10n_in_unit_id')) > 1:
                record.show_l10n_in_unit_id_field = True

    @api.onchange('journal_id')
    def _onchange_journal(self):
        self.l10n_in_unit_id = self.journal_id.l10n_in_unit_id and self.journal_id.unit_id or self.env.user._get_default_unit()
        return super(AccountPayment, self)._onchange_journal()

    def _prepare_payment_moves(self):
        all_move_vals = super(AccountPayment, self)._prepare_payment_moves()
        for move_vals in all_move_vals:
            if move_vals.get('line_ids'):
                move_vals['l10n_in_unit_id'] = self.browse(move_vals['line_ids'][0][2]['payment_id']).l10n_in_unit_id.id
        return move_vals
