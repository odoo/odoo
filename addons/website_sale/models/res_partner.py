from odoo import SUPERUSER_ID, api, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.onchange("property_product_pricelist")
    def _onchange_property_product_pricelist(self):
        open_order = (
            self.env["sale.order"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", self._origin.id),
                    ("pricelist_id", "=", self._origin.property_product_pricelist.id),
                    ("pricelist_id", "!=", self.property_product_pricelist.id),
                    ("website_id", "!=", False),
                    ("state", "=", "draft"),
                ],
                limit=1,
            )
        )

        if open_order:
            return {
                "warning": {
                    "title": self.env._("Open Sale Orders"),
                    "message": self.env._(
                        "This partner has an open cart. "
                        "Please note that the pricelist will not be updated on that cart. "
                        "Also, the cart might not be visible for the customer until you update the pricelist of that cart."
                    ),
                }
            }
        return None

    def _get_current_partner(self, *, order_sudo=False, **kwargs):
        if order_sudo:
            return (
                not order_sudo._is_anonymous_cart() and order_sudo.partner_id
            ) or self.env["res.partner"]
        return super()._get_current_partner(order_sudo=order_sudo, **kwargs)

    def _get_fields_frontend_writable(self):
        frontend_writable_fields = super()._get_fields_frontend_writable()
        frontend_writable_fields.update(
            self.env["ir.model"]
            .with_user(SUPERUSER_ID)
            ._get("res.partner")
            ._get_fields_form_writable()
            .keys()
        )

        return frontend_writable_fields

    def _get_domain_order_fiscal_position_recompute(self):
        return Domain(
            [
                ("state", "=", "draft"),
                ("website_id", "!=", False),
                "|",
                ("partner_id", "in", self.ids),
                ("partner_shipping_id", "in", self.ids),
            ]
        )

    def write(self, vals):
        res = super().write(vals)
        if {"country_id", "vat", "zip"} & vals.keys() and self:
            order_fpos_recompute_domain = (
                self._get_domain_order_fiscal_position_recompute()
            )
            if (
                orders_sudo := self.env["sale.order"]
                .sudo()
                .search(order_fpos_recompute_domain)
            ):
                orders_by_fpos = orders_sudo.grouped("fiscal_position_id")
                self.env.add_to_compute(
                    orders_sudo._fields["fiscal_position_id"], orders_sudo
                )
                if fpos_changed := orders_sudo.filtered(
                    lambda so: so not in orders_by_fpos.get(so.fiscal_position_id, []),
                ):
                    fpos_changed._recompute_taxes()
                    fpos_changed.filtered(
                        lambda order: order.state == "draft"
                    )._recompute_prices()
        return res
