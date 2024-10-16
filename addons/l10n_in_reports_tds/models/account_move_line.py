# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_in_pan = fields.Char(string="PAN NO", related='partner_id.l10n_in_pan')
    l10n_in_base_amount = fields.Monetary(
        string='L10N In Base Amount',
        compute='_compute_base_amount',
        )

    @api.depends('move_id')
    def _compute_base_amount(self):
        for line in self:
            related_move = self.env['account.move'].search([('name', '=', line.move_id.ref)])
            if related_move:
                for move_line in related_move:
                    line.l10n_in_base_amount = move_line.amount_untaxed
            else:
                line.l10n_in_base_amount = line.move_id.amount_untaxed
