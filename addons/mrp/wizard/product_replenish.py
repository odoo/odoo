# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    @api.depends('route_id')
    def _compute_date_planned(self):
        super()._compute_date_planned()
        for rec in self:
            if self.route_id.name == "Manufacture":
                rec.date_planned = rec._get_date_planned(rec.route_id, product_tmpl_id=rec.product_tmpl_id)

    def _get_record_to_notify(self, date):
        order_line = self.env['mrp.production'].search([('write_date', '>=', date)], limit=1)
        return order_line or super()._get_record_to_notify(date)

    def _get_replenishment_order_notification_link(self, production):
        if production._name == 'mrp.production':
            action = self.env.ref('mrp.action_mrp_production_form')
            return [{
                'label': production.name,
                'url': f'#action={action.id}&id={production.id}&model=mrp.production'
            }]
        return super()._get_replenishment_order_notification_link(production)

    def _get_date_planned(self, route_id, **kwargs):
        date = super()._get_date_planned(route_id, **kwargs)
        if route_id.name != 'Manufacture':
            return date
        delay = 0
        product_tmpl_id = kwargs.get('product_tmpl_id') or self.product_tmpl_id
        if bool(self.env['ir.config_parameter'].sudo().get_param('mrp.use_manufacturing_lead')):
            delay += self.env.company.manufacturing_lead
        if product_tmpl_id and product_tmpl_id.bom_ids:
            delay += product_tmpl_id.bom_ids[0].produce_delay + product_tmpl_id.bom_ids[0].days_to_prepare_mo
        return fields.Datetime.add(date, days=delay)
