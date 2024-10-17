# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.base.models.res_partner import WARNING_HELP, WARNING_MESSAGE


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _check_company_auto = True

    property_stock_customer = fields.Many2one(
        'stock.location', string="Customer Location", company_dependent=True, check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="The stock location used as destination when sending goods to this contact.")
    property_stock_supplier = fields.Many2one(
        'stock.location', string="Vendor Location", company_dependent=True, check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="The stock location used as source when receiving goods from this contact.")
    picking_warn = fields.Selection(WARNING_MESSAGE, 'Stock Picking', help=WARNING_HELP, default='no-message')
    picking_warn_msg = fields.Text('Message for Stock Picking')

    def action_view_stock_serial(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("stock.action_production_lot_form")
        action.update({
            'domain': [('partner_ids', '=', self.id)],
            'context': {
                'default_partner_ids': self.id,
            }
        })
        return action
