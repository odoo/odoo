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
        ('partially_pick', 'Partially Pick'),
        ('partially_pack', 'Partially Pack'),
    ],tracking=True,default='draft')
    warehouse_id = fields.Many2one(related='sale_id.warehouse_id', store=True)
    discrete_pick = fields.Boolean(string="Merge Pick", default=False, copy=False)
    automation_manual_order = fields.Selection([
        ('automation', 'Automation'),
        ('manual', 'Manual'),
        ('cross_dock', 'Cross Dock'),
        ('automation_bulk', 'Automation Bulk'),
        ('automation_putaway', 'Automation Putaway'),
        ('merge', 'Merge')
    ], string='Automation/Manual Order', copy=False)
    slsu = fields.Boolean(string="Manual SLSU")
    operation_process_type = fields.Selection(related='picking_type_id.picking_process_type')
    allow_partial = fields.Boolean(string='Allow partial', store='True', default=False)
    is_international = fields.Boolean(
        string='International Shipment',
        compute='_compute_is_international',
        store=True
    )

    @api.depends('partner_id.country_id.code')
    def _compute_is_international(self):
        for picking in self:
            picking.is_international = picking.partner_id.country_id.code != 'AU'

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

    def action_allow_partial(self):
        """
        Marks allow_partial as True when the user clicks the button.
        """
        for rec in self:
            rec.allow_partial = True