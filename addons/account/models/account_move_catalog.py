from collections import defaultdict

from odoo import models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @_debug.perf.timed
    def action_add_from_catalog(self):
        _debug.lifecycle("action_add_from_catalog", records=self)
        res = super().action_add_from_catalog()
        res["search_view_id"] = [
            self.env.ref("account.product_view_search_catalog").id,
            "search",
        ]
        return res

    def _prepare_catalog_extra_context(self):
        res = super()._prepare_catalog_extra_context()
        if self.is_purchase_document() and self.partner_id:
            res["search_default_seller_ids"] = self.partner_id.name

        res["product_catalog_currency_id"] = self.currency_id.id
        res["product_catalog_digits"] = self.line_ids._fields["price_unit"].get_digits(
            self.env
        )
        res["show_sections"] = bool(self.id)
        return res

    def _get_domain_product_catalog(self):
        domain = super()._get_domain_product_catalog()
        if self.is_sale_document():
            return domain & Domain("sale_ok", "=", True)
        elif self.is_purchase_document():
            return domain & Domain("purchase_ok", "=", True)
        else:
            return domain

    def _get_order_line_values(self, child_field=False):
        default_data = super()._get_order_line_values(child_field)
        new_default_data = self.env[
            "account.move.line"
        ]._get_product_catalog_lines_data()
        return {**default_data, **new_default_data}

    def _get_product_catalog_order_data(self, products, **kwargs):
        product_catalog = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            product_catalog[product.id] |= self._get_product_price_and_data(product)
        return product_catalog

    def _get_product_price_and_data(self, product):
        self.check_singleton()
        product_infos = {
            "price": product.list_price
            if self.is_sale_document()
            else product.standard_price
        }

        if self.is_purchase_document() and self.partner_id:
            seller = product._select_seller(
                partner_id=self.partner_id,
                quantity=None,
                date=self.invoice_date,
                uom_id=product.uom_id,
                ordered_by="min_qty",
                params={"order_id": self},
            )
            if seller:
                _debug.logic(
                    "catalog_price_from_seller",
                    move=self,
                    product=product,
                    seller=seller,
                )
                product_infos.update(
                    price=seller.price,
                    min_qty=seller.min_qty,
                )
        return product_infos

    def _get_product_catalog_record_lines(
        self, product_ids, *, section_id=None, **kwargs
    ):
        grouped_lines = defaultdict(lambda: self.env["account.move.line"])
        if section_id is None:
            section_id = (
                self.line_ids[:1].id
                if self.line_ids[:1].display_type == "line_section"
                else False
            )
        for line in self.line_ids:
            if (
                line.get_line_parent_section().id == section_id
                and line.display_type == "product"
                and line.product_id.id in product_ids
            ):
                grouped_lines[line.product_id] |= line
        _debug.pipeline(
            "catalog_lines_grouped",
            move=self,
            section_id=section_id,
            product_count=len(grouped_lines),
        )
        return grouped_lines

    @_debug.perf.timed
    def _update_order_line_info(
        self,
        product_id,
        quantity,
        *,
        section_id=False,
        child_field="line_ids",
        **kwargs,
    ):
        move_line = self.line_ids.filtered(
            lambda line: (
                line.product_id.id == product_id
                and line.get_line_parent_section().id == section_id
            ),
        )[:1]
        _debug.logic(
            "catalog_line_matched",
            move=self,
            product=product_id,
            section=section_id,
            line=move_line,
            quantity=quantity,
        )
        if move_line:
            if quantity != 0:
                move_line.quantity = quantity
            elif self.state == "draft":
                price_unit = self._get_product_price_and_data(move_line.product_id)[
                    "price"
                ]
                _debug.logic("catalog_line_removed", move=self, line=move_line)
                move_line.unlink()
                return price_unit
            else:
                move_line.quantity = 0
        elif quantity > 0:
            move_line = self.env["account.move.line"].create(
                {
                    "move_id": self.id,
                    "quantity": quantity,
                    "product_id": product_id,
                    "sequence": self._get_new_line_sequence(child_field, section_id),
                }
            )
            _debug.pipeline("catalog_line_created", move=self, line=move_line)
        else:
            return 0.0
        return move_line.price_unit

    def _is_readonly(self):
        self.check_singleton()
        return self.state != "draft"

    def _get_parent_field_on_child_model(self):
        return "move_id"

    def _is_line_valid_for_section_line_count(self, line):
        return (
            line.product_id
            and line.product_id.product_tmpl_id.type != "combo"
            and line.quantity > 0
        )
