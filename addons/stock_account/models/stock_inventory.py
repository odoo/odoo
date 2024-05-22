# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    accounting_date = fields.Date(
        'Accounting Date',
        help="Date at which the accounting entries will be created"
             " in case of automated inventory valuation."
             " If empty, the inventory date will be used.")
    has_account_moves = fields.Boolean(compute='_compute_has_account_moves', compute_sudo=True)

    def _compute_has_account_moves(self):
        for inventory in self:
            if inventory.state == 'done' and inventory.move_ids:
                account_move = self.env['account.move'].search_count([
                    ('stock_move_id.id', 'in', inventory.move_ids.ids)
                ])
                inventory.has_account_moves = account_move > 0
            else:
                inventory.has_account_moves = False

    def action_get_account_moves(self):
        self.ensure_one()
        action_data = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action_data['domain'] = [('stock_move_id.id', 'in', self.move_ids.ids)]
        action_data['context'] = dict(self._context, create=False)
        return action_data

    def post_inventory(self):
        res = True
        acc_inventories = self.filtered(lambda inventory: inventory.accounting_date)
        for inventory in acc_inventories:
            res = super(StockInventory, inventory.with_context(force_period_date=inventory.accounting_date)).post_inventory()
        other_inventories = self - acc_inventories
        if other_inventories:
            res = super(StockInventory, other_inventories).post_inventory()
        return res
