# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from email.policy import default

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    current_state = fields.Selection([
        ('draft','Draft'),
        ('pick', 'Pick'),
        ('pack', 'Pack'),
        ('partially_pick', 'Partially Pick')
    ],tracking=True,default='draft')

    warehouse_id = fields.Many2one(related='sale_id.warehouse_id', store=True)

    def action_confirm_geek_pick(self):
        """
        Method to update state to 'pick' and ensure all related move lines are updated properly.
        """
        for record in self:
            if record.state == 'assigned':
                record.sudo().write({'current_state': 'pick'})
                _logger.info(f"Picking {record.name} moved to 'pick' state.")

    def action_confirm_pack(self,):
        """
        Update current_state to 'pack' when packing is confirmed.
        """
        for record in self:
            if record.current_state == 'pick':
                record.current_state = 'pack'
                _logger.info(f"Picking {record.name} moved to 'pack' state {record.state}- {record.current_state}.")