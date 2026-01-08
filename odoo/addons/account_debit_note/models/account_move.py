# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = "account.move"

    debit_origin_id = fields.Many2one('account.move', 'Original Invoice Debited', readonly=True, copy=False, index='btree_not_null')
    debit_note_ids = fields.One2many('account.move', 'debit_origin_id', 'Debit Notes',
                                     help="The debit notes created for this invoice")
    debit_note_count = fields.Integer('Number of Debit Notes', compute='_compute_debit_count')

    @api.depends('debit_note_ids')
    def _compute_debit_count(self):
        debit_data = self.env['account.move']._read_group([('debit_origin_id', 'in', self.ids)],
                                                        ['debit_origin_id'], ['__count'])
        data_map = {debit_origin.id: count for debit_origin, count in debit_data}
        for inv in self:
            inv.debit_note_count = data_map.get(inv.id, 0.0)

    def action_view_debit_notes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Debit Notes'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('debit_origin_id', '=', self.id)],
        }

    def action_debit_note(self):
        action = self.env.ref('account_debit_note.action_view_account_move_debit')._get_action_dict()
        return action
