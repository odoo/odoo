# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.http import request


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

    def _get_current_partner(self, *, order_sudo=False, **kwargs):
        """ Override `portal` to get current partner from order_sudo if user is not signed up. """
        if order_sudo:
            return (
                (not order_sudo._is_anonymous_cart() and order_sudo.partner_id)
                or self.env['res.partner'] # Avoid returning public user's partner
            )
        return super()._get_current_partner(order_sudo=order_sudo, **kwargs)

    def _get_frontend_writable_fields(self):
        """ Override `portal` to make website whitelist fields writable in portal address. """
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update(
            self.env['ir.model']._get('res.partner')._get_form_writable_fields().keys()
        )

        return frontend_writable_fields

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
