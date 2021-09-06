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
from odoo import models, fields, api


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def display_prod_stock(self, product_id):
        warehouse_list = []
        product = self.env['product.product'].browse(product_id)
        for warehouse_obj in self.search([('company_id', '=', self.env.user.company_id.id)]):
            parent_loc_id = warehouse_obj.lot_stock_id.id
            location_list = []
            warehouse_total = []
            warehouse_total_qty = product.with_context({'warehouse': warehouse_obj.id})._product_available()
            warehouse_total.append(warehouse_total_qty[product_id])
            for each in self.env['stock.location'].search([('location_id', 'child_of', parent_loc_id)]):
                available_qty = product.with_context({'location': each.id, 'compute_child': False})._product_available()
                available_qty[product_id].update({'name': each.display_name})
                location_list.append(available_qty[product_id])
            warehouse_list.append({'id': warehouse_obj.id, 'name': warehouse_obj.name,
                                   'locations': location_list, 'Warehouse_total': warehouse_total})
        return warehouse_list
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
