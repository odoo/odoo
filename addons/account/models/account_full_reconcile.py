# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command


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
        def get_ids(commands):
            for command in commands:
                if command[0] == Command.LINK:
                    yield command[1]
                elif command[0] == Command.SET:
                    yield from command[2]
                else:
                    raise ValueError("Unexpected command: %s" % command)
        move_line_ids = [list(get_ids(vals.pop('reconciled_line_ids'))) for vals in vals_list]
        partial_ids = [list(get_ids(vals.pop('partial_reconcile_ids'))) for vals in vals_list]
        fulls = super(AccountFullReconcile, self.with_context(tracking_disable=True)).create(vals_list)

        self.env.cr.execute_values("""
            UPDATE account_move_line line
               SET full_reconcile_id = source.full_id
              FROM (VALUES %s) AS source(full_id, line_ids)
             WHERE line.id = ANY(source.line_ids)
        """, [(full.id, line_ids) for full, line_ids in zip(fulls, move_line_ids)], page_size=1000)
        fulls.reconciled_line_ids.invalidate_recordset(['full_reconcile_id'], flush=False)
        fulls.invalidate_recordset(['reconciled_line_ids'], flush=False)

        self.env.cr.execute_values("""
            UPDATE account_partial_reconcile partial
               SET full_reconcile_id = source.full_id
              FROM (VALUES %s) AS source(full_id, partial_ids)
             WHERE partial.id = ANY(source.partial_ids)
        """, [(full.id, line_ids) for full, line_ids in zip(fulls, partial_ids)], page_size=1000)
        fulls.partial_reconcile_ids.invalidate_recordset(['full_reconcile_id'], flush=False)
        fulls.invalidate_recordset(['partial_reconcile_ids'], flush=False)

        self.env['account.partial.reconcile']._update_matching_number(fulls.reconciled_line_ids)
        return fulls
