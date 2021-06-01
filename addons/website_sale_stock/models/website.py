# -*- coding: utf-8 -*-

from ast import literal_eval

from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    # Deprecated, will be removed in master/saas-14.4 in favor of `stock_location_ids`
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    # Stable fix, no compute/inverse in master/saas-14.4
    stock_location_ids = fields.Many2many('stock.location', string='Locations', compute='_compute_stock_location_ids', inverse='_inverse_stock_location_ids')

    def _compute_stock_location_ids(self):
        ICP = self.env['ir.config_parameter']
        for website in self:
            key = 'website_%s_stock_location_ids' % website.id
            location_ids = literal_eval(ICP.sudo().get_param(key, "[]"))
            website.stock_location_ids = self.env['stock.location'].browse(location_ids)

    def _inverse_stock_location_ids(self):
        for website in self:
            self.env['ir.config_parameter'].sudo().set_param(
                'website_%s_stock_location_ids' % website.id,
                website.stock_location_ids.ids,
            )

    def _prepare_sale_order_values(self, partner, pricelist):
        self.ensure_one()
        values = super(Website, self)._prepare_sale_order_values(partner, pricelist)
        if values['company_id']:
            warehouse_id = (
                self.warehouse_id and self.warehouse_id.id or
                self.env['ir.default'].get('sale.order', 'warehouse_id', company_id=values.get('company_id')) or
                self.env['ir.default'].get('sale.order', 'warehouse_id') or
                self.env['stock.warehouse'].sudo().search([('company_id', '=', values['company_id'])], limit=1).id
            )
            if warehouse_id:
                values['warehouse_id'] = warehouse_id
        return values
