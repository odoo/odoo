import random
from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_is_zero

from odoo.addons.website_sale.models.website import (
    FISCAL_POSITION_SESSION_CACHE_KEY,
    PRICELIST_SELECTED_SESSION_CACHE_KEY,
    PRICELIST_SESSION_CACHE_KEY,
)

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    website_id = fields.Many2one(
        comodel_name="website",
        readonly=True,
        help="Website through which this order was placed for eCommerce orders.",
    )

    cart_recovery_email_sent = fields.Boolean(string="Cart recovery email already sent")
    shop_warning = fields.Char(string="Warning")

    website_order_line = fields.One2many(
        comodel_name="sale.order.line",
        string="Order Lines displayed on Website",
        compute="_compute_website_order_line",
    )
    amount_delivery = fields.Monetary(
        string="Delivery Amount",
        compute="_compute_amount_delivery",
        help="Tax included or excluded depending on the website configuration.",
    )
    cart_quantity = fields.Integer(compute="_compute_cart_info")
    only_services = fields.Boolean(compute="_compute_cart_info")
    is_abandoned_cart = fields.Boolean(
        string="Abandoned Cart",
        compute="_compute_is_abandoned_cart",
        search="_search_abandoned_cart",
    )

    @api.depends("line_ids")
    def _compute_website_order_line(self):
        order_lines = self.env["sale.order.line"].search_fetch(
            [("order_id", "in", self.ids)]
        )
        for order in self:
            order.website_order_line = order_lines.filtered(
                lambda sol, order=order: sol.order_id == order and sol._show_in_cart(),
            )

    @api.depends("line_ids.price_total", "line_ids.price_subtotal")
    def _compute_amount_delivery(self):
        self.amount_delivery = 0.0
        for order in self.filtered("website_id"):
            delivery_lines = order.line_ids.filtered("is_delivery")
            if order.website_id.show_line_subtotals_tax_selection == "tax_excluded":
                order.amount_delivery = sum(delivery_lines.mapped("price_subtotal"))
            else:
                order.amount_delivery = sum(delivery_lines.mapped("price_total"))

    @api.depends("line_ids.product_qty", "line_ids.product_id")
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(
                sum(order.mapped("website_order_line.product_qty"))
            )
            order.only_services = all(
                sol.product_id.type == "service" for sol in order.website_order_line
            )

    @api.depends("website_id", "date_order", "line_ids", "state", "partner_id")
    def _compute_is_abandoned_cart(self):
        for order in self:
            if order.website_id and order.state == "draft" and order.date_order:
                public_partner_id = order.website_id.user_id.partner_id
                abandoned_delay = order.website_id.cart_abandoned_delay or 1.0
                abandoned_datetime = datetime.now(UTC).replace(
                    tzinfo=None
                ) - relativedelta(hours=abandoned_delay)
                order.is_abandoned_cart = bool(
                    order.date_order <= abandoned_datetime
                    and order.partner_id != public_partner_id
                    and order.line_ids
                )
            else:
                order.is_abandoned_cart = False

    def _compute_require_signature(self):
        website_orders = self.filtered("website_id")
        website_orders.require_signature = False
        super(SaleOrder, self - website_orders)._compute_require_signature()

    def _compute_payment_term_id(self):
        super()._compute_payment_term_id()
        website_orders = self.filtered(
            lambda so: so.website_id and not so.payment_term_id
        )
        if not website_orders:
            return

        default_pt = self.env.ref(
            "account.account_payment_term_immediate", raise_if_not_found=False
        )
        first_term_by_company = {}
        for term in self.env["account.payment.term"].search(
            [("company_id", "in", website_orders.company_id.ids)]
        ):
            first_term_by_company.setdefault(term.company_id, term)
        for order in website_orders:
            if default_pt and (
                order.company_id == default_pt.company_id or not default_pt.company_id
            ):
                order.payment_term_id = default_pt
            else:
                order.payment_term_id = first_term_by_company.get(
                    order.company_id, self.env["account.payment.term"]
                )

    def _compute_pricelist_id(self):
        if not (country_code := self.env["website"]._get_geoip_country_code()):
            return super()._compute_pricelist_id()
        if website_orders := self.filtered("website_id"):
            website_orders = website_orders.with_context(country_code=country_code)
            super(SaleOrder, website_orders)._compute_pricelist_id()
        return super(SaleOrder, self - website_orders)._compute_pricelist_id()

    def _search_abandoned_cart(self, operator, value):
        if operator != "in":
            return NotImplemented
        website_ids = self.env["website"].search_read(
            fields=["id", "cart_abandoned_delay", "partner_id"]
        )
        return Domain.AND(
            (
                Domain("state", "=", "draft"),
                Domain("line_ids", "!=", False),
                Domain.OR(
                    [
                        ("website_id", "=", website_id["id"]),
                        (
                            "date_order",
                            "<=",
                            fields.Datetime.to_string(
                                fields.Datetime.now()
                                - relativedelta(
                                    hours=website_id["cart_abandoned_delay"] or 1.0
                                )
                            ),
                        ),
                        ("partner_id", "!=", website_id["partner_id"][0]),
                    ]
                    for website_id in website_ids
                ),
            )
        )

    def _compute_user_id(self):
        website_orders = self.filtered("website_id")
        super(SaleOrder, self - website_orders)._compute_user_id()
        for order in website_orders:
            if order.state == "draft" and not order.env.context.get(
                "force_user_recomputation"
            ):
                continue
            if not order.user_id:
                order.user_id = (
                    order.website_id.salesperson_id
                    or order.partner_id.user_id.id
                    or order.partner_id.parent_id.user_id.id
                )

    def _get_default_sale_team_id(self):
        return super()._get_default_sale_team_id() or self.website_id.salesteam_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("website_id"):
                website = self.env["website"].browse(vals["website_id"])
                if "company_id" in vals:
                    company = self.env["res.company"].browse(vals["company_id"])
                    if website.company_id.id != company.id:
                        _debug.logic(
                            "cart_create_refused",
                            reason="company_mismatch",
                            website=website.id,
                            company=company.id,
                        )
                        raise UserError(
                            _(
                                "The company of the website you are trying to sell from (%(website_company)s)"
                                " is different than the one you want to use (%(company)s)",
                                website_company=website.company_id.name,
                                company=company.name,
                            )
                        )
                else:
                    vals["company_id"] = website.company_id.id
        return super().create(vals_list)

    def action_preview_sale_order(self):
        action = super().action_preview_sale_order()
        if action["url"].startswith("/"):
            action["url"] = f"/@{action['url']}"
        return action

    def action_recovery_email_send(self):
        for order in self:
            order._portal_get_or_create_token()
        composer_form_view_id = self.env.ref(
            "mail.email_compose_message_wizard_form"
        ).id

        template_id = self._get_cart_recovery_template().id

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "view_id": composer_form_view_id,
            "target": "new",
            "context": {
                "default_composition_mode": "mass_mail"
                if len(self.ids) > 1
                else "comment",
                "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
                "default_res_ids": self.ids,
                "default_model": "sale.order",
                "default_template_id": template_id,
                "website_sale_send_recovery_email": True,
            },
        }

    def _get_cart_recovery_template(self):
        websites = self.mapped("website_id")
        template = (
            websites.cart_recovery_mail_template_id if len(websites) == 1 else False
        )
        template = template or self.env.ref(
            "website_sale.mail_template_sale_cart_recovery", raise_if_not_found=False
        )
        return template or self.env["mail.template"]

    def _get_non_delivery_lines(self):
        return self.line_ids.filtered(lambda line: not line.is_delivery)

    def _get_amount_total_excluding_delivery(self):
        return sum(self._get_non_delivery_lines().mapped("price_total"))

    def _get_confirmation_template(self):
        self.check_singleton()

        if self.website_id and self.website_id.confirmation_email_template_id:
            return self.website_id.confirmation_email_template_id

        return super()._get_confirmation_template()

    def action_confirm(self):
        carts = self.filtered("website_id")
        if self.env.su:
            carts = carts.with_user(SUPERUSER_ID)
        carts.with_context(force_user_recomputation=True)._compute_user_id()
        return super().action_confirm()

    def _send_mail_order_payment_succeeded(self):
        if carts := self.filtered("website_id"):
            carts.with_context(force_user_recomputation=True)._compute_user_id()
        return super()._send_mail_order_payment_succeeded()

    @api.model
    def _get_note_url(self):
        website_id = self.env.context.get("website_id")
        if website_id:
            return self.env["website"].browse(website_id).get_base_url()
        return super()._get_note_url()

    def _is_customer_address_required(self):
        return True

    def _update_address(self, partner_id, fnames=None):
        if not fnames:
            return

        fpos_before = self.fiscal_position_id
        pricelist_before = self.pricelist_id

        self.write(dict.fromkeys(fnames, partner_id))

        fpos_changed = fpos_before != self.fiscal_position_id
        if fpos_changed:
            self._recompute_taxes()

            new_fpos = self.fiscal_position_id
            request.session[FISCAL_POSITION_SESSION_CACHE_KEY] = new_fpos.id
            request.fiscal_position = new_fpos

        if selected_pricelist_id := request.session.get(
            PRICELIST_SELECTED_SESSION_CACHE_KEY
        ):
            selected_pricelist = (
                self.env["product.pricelist"].browse(selected_pricelist_id).exists()
            )
            if (
                selected_pricelist
                and selected_pricelist._is_available_on_website(self.website_id)
                and selected_pricelist._is_available_in_country(
                    self.partner_id.country_id.code
                )
            ):
                self.pricelist_id = selected_pricelist
            else:
                request.session.pop(PRICELIST_SELECTED_SESSION_CACHE_KEY, None)

        if self.pricelist_id != pricelist_before or fpos_changed:
            self._recompute_prices()

            new_pricelist = self.pricelist_id
            request.session[PRICELIST_SESSION_CACHE_KEY] = new_pricelist.id
            request.pricelist = new_pricelist

        if (
            self.carrier_id
            and "partner_shipping_id" in fnames
            and self._has_deliverable_products()
        ):
            delivery_methods = self._get_delivery_methods()
            delivery_method = self._get_preferred_delivery_method(delivery_methods)
            self._set_delivery_method(delivery_method)

    def _cart_add(
        self,
        product_id: int,
        quantity: float = 1.0,
        *,
        uom_id: int | None = None,
        **kwargs,
    ) -> dict:
        self.check_singleton()
        self = self.with_company(self.company_id)

        if not uom_id:
            uom_id = self.env["product.product"].browse(product_id).uom_id.id  # type: ignore[attr-defined]
        if existing_sol := self._cart_find_product_line(
            product_id, uom_id=uom_id, **kwargs
        )[:1]:
            _debug.logic(
                "cart_add",
                by="merged_into_line",
                order=self.id,
                product=product_id,
                line=existing_sol.id,
            )
            return self._cart_update_line_quantity(
                line_id=existing_sol.id,  # type: ignore[attr-defined]
                quantity=existing_sol.product_qty + quantity,
                **kwargs,
            )

        quantity, warning = self._get_updated_quantity(
            self.env["sale.order.line"],
            product_id,
            quantity,
            uom_id=uom_id,
            **kwargs,
        )

        order_line = self._create_new_cart_line(product_id, quantity, uom_id, **kwargs)
        _debug.lifecycle(
            "cart_line_created",
            order=self.id,
            product=product_id,
            line=order_line.id,
            quantity=quantity,
        )

        if warning:
            _debug.logic("cart_warning", order=self.id, by="add")
            (order_line or self).shop_warning = warning

        if not self.env.context.get("skip_cart_verification"):
            self._sync_cart_after_update()

        return {
            "added_qty": quantity,
            "line_id": order_line.id,
            "quantity": quantity,
            "warning": warning,
        }

    def _cart_find_product_line(
        self,
        product_id,
        uom_id,
        linked_line_id=False,
        no_variant_attribute_value_ids=None,
        **kwargs,
    ):
        self.check_singleton()

        if not self.line_ids:
            return self.env["sale.order.line"]

        product = self.env["product.product"].browse(product_id)
        if product.type == "combo":
            return self.env["sale.order.line"]

        domain = [
            ("product_id", "=", product_id),
            ("product_uom_id", "=", uom_id),
            ("product_custom_attribute_value_ids", "=", False),
            ("linked_line_id", "=", linked_line_id),
            ("combo_item_id", "=", False),
        ]

        filtered_sol = self.line_ids.filtered_domain(domain)
        if not filtered_sol:
            return self.env["sale.order.line"]

        has_configurable_no_variant_attributes = any(
            len(line.value_ids) > 1 or line.attribute_id.display_type == "multi"
            for line in product.attribute_line_ids
            if line.attribute_id.create_variant == "no_variant"
        )
        if has_configurable_no_variant_attributes:
            filtered_sol = filtered_sol.filtered(
                lambda sol: (
                    sol.product_no_variant_attribute_value_ids.ids
                    == no_variant_attribute_value_ids
                )
            )

        return filtered_sol

    def _cart_update_line_quantity(
        self, line_id: int, quantity: float, **kwargs
    ) -> dict:
        if self:
            self.check_singleton()

        self = self.with_company(self.company_id)

        if not (order_line := self.line_ids.filtered(lambda sol: sol.id == line_id)):
            _debug.logic(
                "cart_update_refused",
                reason="line_not_in_cart",
                order=self.id,
                line=line_id,
            )
            return {
                "warning": _(
                    "We weren't able to update your cart. Please refresh your page before trying"
                    " again."
                )
            }

        if quantity > 0:
            quantity, warning = self._get_updated_quantity(
                order_line,
                order_line.product_id.id,
                quantity,
                uom_id=order_line.product_uom_id.id,
                **kwargs,
            )
        else:
            warning = ""

        added_qty = quantity - order_line.product_qty
        _debug.lifecycle(
            "cart_line_quantity",
            order=self.id,
            line=line_id,
            quantity=quantity,
            added=added_qty,
        )
        order_line = self._cart_update_order_line(order_line, quantity, **kwargs)
        if not self.env.context.get("skip_cart_verification"):
            self._sync_cart_after_update()

        if warning:
            (order_line or self).shop_warning = warning

        return {
            "added_qty": added_qty,
            "line_id": order_line.id,
            "quantity": quantity,
            "warning": warning,
        }

    def _get_updated_quantity(self, order_line, product_id, new_qty, uom_id, **kwargs):
        return new_qty, ""

    def _cart_update_order_line(self, order_line, quantity, **kwargs):
        self.check_singleton()
        order_line.check_singleton()

        if quantity <= 0:
            order_line.unlink()
            return self.env["sale.order.line"]

        update_values = self._prepare_order_line_update_values(
            order_line, quantity, **kwargs
        )
        if update_values:
            combo_item_lines = order_line.linked_line_ids.filtered("combo_item_id")
            if (
                order_line.product_type == "combo"
                and combo_item_lines
                and "product_qty" in update_values
            ):
                combo_quantity = quantity
                for item_line in combo_item_lines:
                    if quantity != item_line.product_qty:
                        combo_item_quantity, _warning = self._get_updated_quantity(
                            item_line,
                            item_line.product_id.id,
                            quantity,
                            uom_id=item_line.product_uom_id.id,
                            **kwargs,
                        )
                        combo_quantity = min(combo_quantity, combo_item_quantity)
                for item_line in combo_item_lines:
                    if combo_quantity != item_line.product_qty:
                        self.with_context(
                            skip_cart_verification=True
                        )._cart_update_line_quantity(
                            line_id=item_line.id, quantity=combo_quantity
                        )
                update_values["product_qty"] = combo_quantity

            order_line.write(update_values)
            if "product_qty" in update_values:
                order_line.invalidate_recordset(["pricelist_item_id"])
                order_line.with_context(
                    force_price_recomputation=True
                )._compute_price_and_discount()

            order_line._check_validity()

        return order_line

    def _prepare_order_line_update_values(self, order_line, quantity, **kwargs):
        self.check_singleton()
        values = {}

        if quantity != order_line.product_qty:
            values["product_qty"] = quantity

        return values

    def _create_new_cart_line(self, product_id, quantity, uom_id, **kwargs):
        if quantity <= 0.0:
            return self.env["sale.order.line"]

        line = self.env["sale.order.line"].create(
            self._prepare_order_line_values(product_id, quantity, uom_id, **kwargs)
        )

        if line.product_type != "combo":
            line._check_validity()
        return line

    def _prepare_order_line_values(
        self,
        product_id,
        quantity,
        uom_id,
        *,
        linked_line_id=False,
        no_variant_attribute_value_ids=None,
        product_custom_attribute_values=None,
        combo_item_id=None,
        **kwargs,
    ):
        self.check_singleton()
        product = self.env["product.product"].browse(product_id)

        no_variant_attribute_values = product.env[
            "product.template.attribute.value"
        ].browse(no_variant_attribute_value_ids)
        received_combination = (
            product.product_template_attribute_value_ids | no_variant_attribute_values
        )
        product_template = product.product_tmpl_id

        combination = product_template._get_closest_possible_combination(
            received_combination
        )

        product = product_template._create_product_variant(combination)

        if not product:
            _debug.logic("cart_line_refused", reason="no_variant", order=self.id)
            raise UserError(
                _(
                    "The given combination does not exist therefore it cannot be added to cart."
                )
            )

        if linked_line_id and linked_line_id not in self.line_ids.ids:
            raise UserError(_("Invalid request parameters."))

        values = {
            "product_id": product.id,
            "product_qty": quantity,
            "product_uom_id": uom_id or product.uom_id.id,
            "order_id": self.id,
            "linked_line_id": linked_line_id,
            "combo_item_id": combo_item_id,
        }

        no_variant_attribute_values |= combination.filtered(
            lambda ptav: ptav.attribute_id.create_variant == "no_variant"
        )

        if no_variant_attribute_values:
            values["product_no_variant_attribute_value_ids"] = [
                Command.set(no_variant_attribute_values.ids)
            ]

        custom_values = product_custom_attribute_values or []
        received_custom_values = product.env["product.template.attribute.value"].browse(
            [
                int(ptav["custom_product_template_attribute_value_id"])
                for ptav in custom_values
            ]
        )

        for ptav in combination.filtered(
            lambda ptav: ptav.is_custom and ptav not in received_custom_values
        ):
            custom_values.append(
                {
                    "custom_product_template_attribute_value_id": ptav.id,
                    "custom_value": "",
                }
            )

        if custom_values:
            values["product_custom_attribute_value_ids"] = [
                fields.Command.create(
                    {
                        "custom_product_template_attribute_value_id": custom_value[
                            "custom_product_template_attribute_value_id"
                        ],
                        "custom_value": custom_value["custom_value"],
                    }
                )
                for custom_value in custom_values
            ]

        return values

    def _check_combo_quantities(self, line) -> bool:
        if not (combo_lines := line.linked_line_ids):
            return False
        available_combo_quantity = min(line.product_qty for line in combo_lines)
        if available_combo_quantity < line.product_qty:
            line._set_shop_warning_stock(
                line.product_qty,
                available_combo_quantity,
            )
            (line + combo_lines).product_qty = available_combo_quantity
            return True

        return False

    def _sync_cart_after_update(self):
        if self.only_services:
            _debug.logic("cart_delivery", by="services_only", order=self.id)
            self._remove_delivery_line()
        elif self.carrier_id:
            rate = self.carrier_id.rate_shipment(self)
            _debug.logic(
                "cart_delivery",
                by="rated" if rate["success"] else "rate_failed",
                order=self.id,
                carrier=self.carrier_id.id,
            )
            if rate["success"]:
                self.line_ids.filtered("is_delivery").price_unit = rate["price"]
            else:
                self._remove_delivery_line()

        if request:
            request.session["website_sale_cart_quantity"] = self.cart_quantity

    def _remove_invalid_cart_lines(self):
        self.check_singleton()

        self.line_ids.filtered(
            lambda sol: sol.product_id and not sol.product_id.active
        ).unlink()

    def _cart_accessories(self):
        product_ids = set(self.website_order_line.product_id.ids)
        all_accessory_products = self.env["product.product"]
        for line in self.website_order_line.filtered("product_id"):
            accessory_products = (
                line.product_id.product_tmpl_id._get_website_accessory_product()
            )
            if accessory_products:
                combination = (
                    line.product_id.product_template_attribute_value_ids
                    + line.product_no_variant_attribute_value_ids
                )
                all_accessory_products |= accessory_products.filtered(
                    lambda product, line=line, combination=combination: (
                        product.id not in product_ids
                        and product._website_show_quick_add()
                        and product.filtered_domain(
                            self.env["product.product"]._check_company_domain(
                                line.company_id
                            )
                        )
                        and product._is_variant_possible(parent_combination=combination)
                        and (
                            not self.website_id.prevent_zero_price_sale
                            or product._get_contextual_price()
                        )
                    )
                )

        _debug.perf.count(
            "cart_accessories",
            order=self.id,
            lines=len(self.website_order_line),
            accessories=len(all_accessory_products),
        )
        return random.sample(all_accessory_products, len(all_accessory_products))

    def _cart_recovery_email_send(self):
        sent_orders = self.env["sale.order"]
        for order in self:
            template = order._get_cart_recovery_template()
            if template:
                order._portal_get_or_create_token()
                template.send_mail(order.id)
                sent_orders |= order
        _debug.lifecycle(
            "cart_recovery_mails",
            orders=self,
            considered=len(self),
            sent=len(sent_orders),
        )
        sent_orders.write({"cart_recovery_email_sent": True})

    def _message_mail_after_hook(self, mails):
        if self.env.context.get("website_sale_send_recovery_email"):
            self.filtered_domain(
                [
                    ("cart_recovery_email_sent", "=", False),
                    ("is_abandoned_cart", "=", True),
                ]
            ).cart_recovery_email_sent = True
        return super()._message_mail_after_hook(mails)

    def _message_post_after_hook(self, message, msg_vals):
        if self.env.context.get("website_sale_send_recovery_email"):
            self.cart_recovery_email_sent = True
        return super()._message_post_after_hook(message, msg_vals)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.check_singleton()
        customer_portal_group = next(
            (group for group in groups if group[0] == "portal_customer"), None
        )
        if customer_portal_group:
            access_opt = customer_portal_group[2].setdefault("button_access", {})
            if self.env.context.get("website_sale_send_recovery_email"):
                access_opt["title"] = _("Resume Order")
                access_opt["url"] = (
                    f"{self.get_base_url()}/shop/cart?id={self.id}&access_token={self.access_token}"
                )
        return groups

    def _is_reorder_allowed(self):
        self.check_singleton()
        return self.state == "done" and any(
            line._is_reorder_allowed() for line in self.line_ids if line.product_id
        )

    def _filter_can_send_abandoned_cart_mail(self):
        self.website_id.check_singleton()
        abandoned_datetime = datetime.now(UTC) - relativedelta(
            hours=self.website_id.cart_abandoned_delay
        )

        sales_after_abandoned_date = self.env["sale.order"].search(
            [
                ("state", "=", "done"),
                ("partner_id", "in", self.partner_id.ids),
                ("create_date", ">=", abandoned_datetime),
                ("website_id", "=", self.website_id.id),
            ]
        )
        latest_create_date_per_partner = {}
        for sale in self:
            if sale.partner_id not in latest_create_date_per_partner:
                latest_create_date_per_partner[sale.partner_id] = sale.create_date
            else:
                latest_create_date_per_partner[sale.partner_id] = max(
                    latest_create_date_per_partner[sale.partner_id], sale.create_date
                )
        has_later_sale_order = {}
        for sale in sales_after_abandoned_date:
            if has_later_sale_order.get(sale.partner_id):
                continue
            has_later_sale_order[sale.partner_id] = (
                latest_create_date_per_partner[sale.partner_id] <= sale.date_order
            )

        return self.filtered(
            lambda abandoned_sale_order: (
                abandoned_sale_order.partner_id.email
                and not any(
                    transaction.sudo().state == "error"
                    for transaction in abandoned_sale_order.transaction_ids
                )
                and any(
                    not float_is_zero(
                        line.price_unit, precision_rounding=line.currency_id.rounding
                    )
                    for line in abandoned_sale_order.line_ids
                )
                and not has_later_sale_order.get(abandoned_sale_order.partner_id)
            )
        )

    def _has_deliverable_products(self):
        return bool(self.line_ids.product_id) and not self.only_services

    def _remove_delivery_line(self):
        super()._remove_delivery_line()
        self.pickup_location_data = {}

    def _get_preferred_delivery_method(self, available_delivery_methods):
        self.check_singleton()

        delivery_method = self.carrier_id
        if (
            available_delivery_methods
            and delivery_method not in available_delivery_methods
        ):
            if (
                self.partner_shipping_id.property_delivery_carrier_id
                in available_delivery_methods
            ):
                delivery_method = self.partner_shipping_id.property_delivery_carrier_id
            else:
                delivery_method = available_delivery_methods[0]
        return delivery_method

    def _set_delivery_method(self, delivery_method, rate=None):
        self.check_singleton()

        self._remove_delivery_line()
        if not delivery_method or not self._has_deliverable_products():
            return

        rate = rate or delivery_method.rate_shipment(self)
        if rate.get("success"):
            self.set_delivery_line(delivery_method, rate["price"])

    def _get_delivery_methods(self):
        return (
            self.env["delivery.carrier"]
            .sudo()
            .search(
                [
                    ("website_published", "=", True),
                    *self.env["delivery.carrier"]._check_company_domain(
                        self.company_id
                    ),
                ]
            )
            .filtered(lambda carrier: carrier._is_available_for_order(self))
        )

    def _is_anonymous_cart(self):
        self.check_singleton()
        return self.partner_id.id == request.website.user_id.sudo().partner_id.id

    def _get_lang(self):
        res = super()._get_lang()

        if self.website_id and request and request.is_frontend:
            return request.env.lang

        return res

    def _get_shop_warning(self, clear=True):
        self.check_singleton()
        warn = self.shop_warning
        if clear:
            self.shop_warning = ""
        return warn

    def _is_cart_ready(self):
        return bool(self)

    def _check_cart_is_ready_to_be_paid(self):
        if not self._is_cart_ready():
            raise ValidationError(
                _("Your cart is not ready to be paid, please verify previous steps.")
            )

        if not self.only_services:
            if not self.carrier_id:
                raise ValidationError(_("No shipping method is selected."))
            if self.carrier_id not in self._get_delivery_methods():
                raise ValidationError(
                    _(
                        "The delivery method is not compatible with your delivery address."
                    )
                )

    def _recompute_cart(self):
        self._recompute_taxes()
        self._recompute_prices()
