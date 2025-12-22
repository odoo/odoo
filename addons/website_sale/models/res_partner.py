# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.addons.website.models import ir_http


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_website_so_id = fields.Many2one(
        string="Last Online Sales Order",
        comodel_name='sale.order',
        compute='_compute_last_website_so_id',
    )

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

    def _can_be_edited_by_current_customer(self, sale_order, address_type):
        self.ensure_one()
        children_partner_ids = self.env['res.partner']._search([
            ('id', 'child_of', sale_order.partner_id.commercial_partner_id.id),
            ('type', 'in', ('invoice', 'delivery', 'other')),
        ])
        return self == sale_order.partner_id or self.id in children_partner_ids

    def write(self, vals):
        res = super().write(vals)
        if {'country_id', 'vat', 'zip'} & vals.keys():
            # Recompute fiscal position for open website orders
            if orders_sudo := self.env['sale.order'].sudo().search([
                ('state', '=', 'draft'),
                ('website_id', '!=', False),
                '|', ('partner_id', 'in', self.ids), ('partner_shipping_id', 'in', self.ids),
            ]):
                orders_by_fpos = orders_sudo.grouped('fiscal_position_id')
                self.env.add_to_compute(orders_sudo._fields['fiscal_position_id'], orders_sudo)
                if fpos_changed := orders_sudo.filtered(
                    lambda so: so not in orders_by_fpos.get(so.fiscal_position_id, []),
                ):
                    fpos_changed._recompute_taxes()
                    fpos_changed._recompute_prices()
        return res
