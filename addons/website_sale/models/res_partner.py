# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.website.models import ir_http


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_website_so_id = fields.Many2one('sale.order', compute='_compute_last_website_so_id', string='Last Online Sales Order')

    def _compute_last_website_so_id(self):
        SaleOrder = self.env['sale.order']
        for partner in self:
            is_public = partner.is_public
            website = ir_http.get_request_website()
            if website and not is_public:
                partner.last_website_so_id = SaleOrder.search([
                    ('partner_id', '=', partner.id),
                    ('pricelist_id', '=', partner.property_product_pricelist.id),
                    ('website_id', '=', website.id),
                    ('state', '=', 'draft'),
                ], order='write_date desc', limit=1)
            else:
                partner.last_website_so_id = SaleOrder  # Not in a website context or public User

    @api.onchange('property_product_pricelist')
    def _onchange_property_product_pricelist(self):
        open_order = self.env['sale.order'].sudo().search([
            ('partner_id', '=', self._origin.id),
            ('pricelist_id', '=', self._origin.property_product_pricelist.id),
            ('pricelist_id', '!=', self.property_product_pricelist.id),
            ('website_id', '!=', False),
            ('state', '=', 'draft'),
        ], limit=1)

        if open_order:
            return {'warning': {
                'title': _('Open Sale Orders'),
                'message': _(
                    "This partner has an open cart. "
                    "Please note that the pricelist will not be updated on that cart. "
                    "Also, the cart might not be visible for the customer until you update the pricelist of that cart."
                ),
            }}

    def write(self, vals):
        res = super().write(vals)
        if {'country_id', 'vat', 'zip'} & vals.keys():
            # Recompute fiscal position for open website orders
            orders_sudo = self.env['sale.order'].sudo().search([
                ('state', '=', 'draft'),
                ('website_id', '!=', False),
                '|', ('partner_id', 'in', self.ids), ('partner_shipping_id', 'in', self.ids),
            ])
            if orders_sudo:
                fpos_by_order = {so.id: so.fiscal_position_id.id for so in orders_sudo}
                self.env.add_to_compute(orders_sudo._fields['fiscal_position_id'], orders_sudo)
                fpos_changed = orders_sudo.filtered(
                    lambda so: so.fiscal_position_id.id != fpos_by_order[so.id],
                )
                if fpos_changed:
                    fpos_changed._recompute_taxes()
                    fpos_changed._recompute_prices()
        return res
