# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    show_bom = fields.Boolean('Show BoM column', compute='_compute_show_bom')
    bom_id = fields.Many2one(
        'mrp.bom', string='Bill of Materials', check_company=True,
        domain="[('type', '=', 'normal'), '&', '|', ('company_id', '=', company_id), ('company_id', '=', False), '|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]")

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        production = self.env['mrp.production'].search([
            ('orderpoint_id', 'in', self.ids)
        ], order='create_date desc', limit=1)
        if production:
            action = self.env.ref('mrp.action_mrp_production_form')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('The following replenishment order has been generated'),
                    'message': '%s',
                    'links': [{
                        'label': production.name,
                        'url': f'#action={action.id}&id={production.id}&model=mrp.production'
                    }],
                    'sticky': False,
                }
            }
        return super()._get_replenishment_order_notification()

    @api.depends('route_id')
    def _compute_show_bom(self):
        manufacture_route = []
        for res in self.env['stock.rule'].search_read([('action', '=', 'manufacture')], ['route_id']):
            manufacture_route.append(res['route_id'][0])
        for orderpoint in self:
            orderpoint.show_bom = orderpoint.route_id.id in manufacture_route

    def _set_default_route_id(self):
        route_id = self.env['stock.rule'].search([
            ('action', '=', 'manufacture')
        ]).route_id
        orderpoint_wh_bom = self.filtered(lambda o: o.product_id.bom_ids)
        if route_id and orderpoint_wh_bom:
            orderpoint_wh_bom.route_id = route_id[0].id
        return super()._set_default_route_id()

    def _prepare_procurement_values(self, date=False, group=False):
        values = super()._prepare_procurement_values(date=date, group=group)
        values['bom_id'] = self.bom_id
        return values
