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

from odoo import api, fields, models, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    state_check = fields.Selection(related='lot_id.state_check', string="state", store=True)

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
                                   in_date=None):
        result = super(StockQuant, self)._update_available_quantity(product_id, location_id, quantity, lot_id,
                                                                    package_id, owner_id, in_date)
        if product_id.filtered(lambda product: product.is_material_monitor):
            notifications = []
            quant_vals = {}
            product_detail_id = []
            if location_id and location_id.usage == 'internal':
                quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                                      strict=True)
                product_id = quants.product_id.with_context({'location': location_id.id, 'compute_child': False})
                product_detail_id = [{
                    'location_id': location_id.id,
                    'product_id': quants.product_id.id,
                    'quantity': product_id.qty_available,
                }]
            user_ids = self.env['res.users'].sudo().search([]).filtered(
                lambda user: user.has_group('flexipharmacy.group_material_monitor_user'))
            for user_id in user_ids:
                notifications.append([(self._cr.dbname, 'customer.display', user_id.id),
                                      {'updeted_location_vals_qty': product_detail_id}])
            self.env['bus.bus'].sendmany(notifications)
        return result
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
