# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    remaining_qty = fields.Float("Remaining Qty", compute="_compute_remaining_qty")
    expiry_state = fields.Selection([('expired', 'Expired'), ('near_expired', 'Near Expired')], string="State", compute='_get_production_lot_state')
    state_check = fields.Selection([('Expired', 'Expired'), ('Near Expired', 'Near Expired')], string="Expiry State")
    product_expiry_reminder = fields.Boolean(compute='_compute_product_expiry_reminder', help="The Expiration Date has been reached.")

    @api.depends('alert_date')
    def _compute_product_expiry_reminder(self):
        current_date = fields.Datetime.now()
        for lot in self:
            if lot.alert_date and not lot.product_expiry_alert:
                lot.product_expiry_reminder = lot.alert_date <= current_date
            else:
                lot. product_expiry_reminder = False

    @api.model
    def name_search(self, name, args=None, operator='=', limit=100):
        if self._context.get('default_product_id'):
            stock_production_lot_obj = self.env['stock.production.lot']
            args = args or []
            recs = self.search([('product_id', '=', self._context.get('default_product_id'))])
            if recs:
                for each_stock_lot in recs.filtered(lambda l: l.expiration_date).sorted(key=lambda p: (p.expiration_date),
                                                                                  reverse=False):
                    if each_stock_lot.expiry_state != 'expired':
                        stock_production_lot_obj |= each_stock_lot
                return stock_production_lot_obj.name_get()
        return super(StockProductionLot, self).name_search(name, args, operator, limit)

    @api.model
    def product_state_check(self):
        today_date = date.today()
        for each_stock_lot in self.filtered(lambda l: l.expiration_date):
            if each_stock_lot.product_id.tracking != 'none':
                expiration_date = datetime.strptime(str(each_stock_lot.expiration_date), '%Y-%m-%d %H:%M:%S').date()
                if expiration_date < today_date:
                    each_stock_lot.write({'state_check': 'Expired'})
                else:
                    if each_stock_lot.alert_date:
                        alert_date = datetime.strptime(str(each_stock_lot.alert_date), '%Y-%m-%d %H:%M:%S').date()
                        if alert_date <= today_date:
                            each_stock_lot.write({'state_check': 'Near Expired'})
            else:
                each_stock_lot.write({'state_check': ''})

    @api.depends('alert_date', 'expiration_date')
    def _get_production_lot_state(self):
        today_date = date.today()
        for each_stock_lot in self:
            each_stock_lot.expiry_state = ''
            each_stock_lot.state_check = ''
            if each_stock_lot.product_expiry_alert:
                each_stock_lot.expiry_state = 'expired'
                each_stock_lot.state_check = 'Expired'
            if each_stock_lot.product_expiry_reminder:
                each_stock_lot.expiry_state = 'near_expired'
                each_stock_lot.state_check = 'Near Expired'

    def _compute_remaining_qty(self):
        for each in self:
            each.remaining_qty = 0
            for quant_id in each.quant_ids:
                if quant_id and quant_id.location_id and quant_id.location_id.usage == 'internal':
                    each.remaining_qty += quant_id.quantity
        return

    def product_lot_and_serial(self, product_id, picking_type):
        picking_type_id = self.env['stock.picking.type'].browse(picking_type)
        domain = [('product_id', '=', product_id)]
        product_expiry_module_id = self.env['ir.module.module'].sudo().search([('name', '=', 'product_expiry')])
        if product_expiry_module_id.state == 'installed':
            domain += ('|', ('expiration_date', '>', datetime.utcnow().date().strftime("%Y-%m-%d")),
                       ('expiration_date', '=', False))
        lot_ids = self.env['stock.production.lot'].search_read(domain)
        for lot_id in lot_ids:
            quant_ids = self.env['stock.quant'].search([('id', 'in', lot_id.get('quant_ids')), (
            'location_id', '=', picking_type_id.default_location_src_id.id), ('on_hand', '=', True)])
            if quant_ids and quant_ids.quantity >= 0:
                lot_id.update({
                    'location_product_qty': quant_ids.quantity
                })
            else:
                lot_id.update({
                    'location_product_qty': 0
                })
        return lot_ids
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
