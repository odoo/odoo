# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

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

    def _can_be_edited_by_current_customer(self, sale_order, address_type):
        self.ensure_one()
        children_partner_ids = self.env['res.partner']._search([
            ('id', 'child_of', sale_order.partner_id.commercial_partner_id.id),
            ('type', 'in', ('invoice', 'delivery', 'other')),
        ])
        return self == sale_order.partner_id or self.id in children_partner_ids
