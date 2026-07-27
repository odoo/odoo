# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
    picking_warn_msg = fields.Text('Message for Stock Picking')

    def action_view_stock_serial(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("stock.action_production_lot_form")
        action['domain'] = [('partner_ids', 'child_of', self.ids)]
        action["context"] = {
            "display_complete": True,
            "create": True,
            "default_partner_ids": self.ids,
        }
        return action

    def write(self, vals):
        res = super().write(vals)
        if 'company_id' in vals:
            lots = self.env['stock.lot'].search([('company_id', '!=', False), ('partner_ids', 'in', self.ids)])
            for lot in lots:
                if invalid_partners := lot.partner_ids.filtered(lambda p: p.company_id != lot.company_id):
                    lot.partner_ids -= invalid_partners
        return res
