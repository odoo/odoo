# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class RepairkWarnUncompleteMove(models.TransientModel):
    _name = 'repair.warn.uncomplete.move'
    _description = 'Warn Uncomplete Move(s)'

    repair_ids = fields.Many2many('repair.order', string='Repair Orders')

    def action_validate(self):
        self.ensure_one()
        return self.repair_ids.action_repair_done()
