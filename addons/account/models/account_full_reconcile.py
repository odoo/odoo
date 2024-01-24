# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountFullReconcile(models.Model):
    _name = "account.full.reconcile"
    _description = "Full Reconcile"

    partial_reconcile_ids = fields.One2many('account.partial.reconcile', 'full_reconcile_id', string='Reconciliation Parts')
    reconciled_line_ids = fields.One2many('account.move.line', 'full_reconcile_id', string='Matched Journal Items')
    exchange_move_id = fields.Many2one('account.move', index="btree_not_null")

    def unlink(self):
        """ When removing a full reconciliation, we need to revert the eventual journal entries we created to book the
            fluctuation of the foreign currency's exchange rate.
            We need also to reconcile together the origin currency difference line and its reversal in order to completely
            cancel the currency difference entry on the partner account (otherwise it will still appear on the aged balance
            for example).
        """
        # Avoid cyclic unlink calls when removing partials.
        if not self:
            return True

        moves_to_reverse = self.exchange_move_id

        res = super().unlink()

        # Reverse all exchange moves at once.
        if moves_to_reverse:
            default_values_list = [{
                'date': move._get_accounting_date(move.date, move._affect_tax_report()),
                'ref': _('Reversal of: %s', move.name),
            } for move in moves_to_reverse]
            moves_to_reverse._reverse_moves(default_values_list, cancel=True)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        fulls = super().create(vals_list)
        for full in fulls.with_context(skip_matching_number_check=True):
            full.reconciled_line_ids.matching_number = str(full.id)
        return fulls
