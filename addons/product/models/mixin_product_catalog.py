from odoo import _, api, models
from odoo.fields import Domain


class MixinProductCatalog(models.AbstractModel):
    _name = "mixin.product.catalog"
    _description = "Product Catalog Mixin"

    @api.readonly
    def action_add_from_catalog(self):
        self.check_singleton()
        kanban_view_id = self.env.ref("product.view_product_product_kanban_catalog").id
        search_view_id = self.env.ref("product.view_product_product_search_catalog").id
        additional_context = self._prepare_catalog_extra_context()
        return {
            "type": "ir.actions.act_window",
            "name": _("Products"),
            "res_model": "product.product",
            "views": [(kanban_view_id, "kanban"), (False, "form")],
            "search_view_id": [search_view_id, "search"],
            "domain": self._get_domain_product_catalog(),
            "context": {**self._prepare_catalog_action_context(), **additional_context},
        }

    def _prepare_catalog_action_context(self):
        return {
            key: value
            for key, value in self.env.context.items()
            if not key.startswith("default_")
        }

    def _get_order_line_values(self, child_field=False):
        return {
            "quantity": 0,
            "readOnly": self._is_readonly() if self else False,
        }

    def _get_domain_product_catalog(self) -> Domain:
        return (
            Domain("company_id", "=", False)
            | Domain("company_id", "parent_of", self.company_id.id)
        ) & Domain("type", "!=", "combo")

    def _get_product_catalog_record_lines(self, product_ids, **kwargs):
        return {}

    def _get_product_catalog_order_data(self, products, **kwargs):
        return {
            product.id: {
                "productType": product.type,
                "uomDisplayName": product.uom_id.display_name,
                "code": product.code or "",
            }
            for product in products
        }

    def _get_product_catalog_order_line_info(
        self, product_ids, child_field=False, **kwargs
    ):
        order_line_info = {}

        for product, record_lines in self._get_product_catalog_record_lines(
            product_ids, child_field=child_field, **kwargs
        ).items():
            order_line_info[product.id] = {
                **record_lines._get_product_catalog_lines_data(
                    parent_record=self, **kwargs
                ),
                "productType": product.type,
                "code": product.code or "",
            }
            if not order_line_info[product.id].get("uomDisplayName"):
                order_line_info[product.id]["uomDisplayName"] = (
                    product.uom_id.display_name
                )

        default_data = self._get_order_line_values(child_field)
        products = self.env["product.product"].browse(product_ids)
        product_data = self._get_product_catalog_order_data(products, **kwargs)

        for product_id, data in product_data.items():
            if product_id in order_line_info:
                continue
            order_line_info[product_id] = {**default_data, **data}

        return order_line_info

    def _prepare_catalog_extra_context(self):
        return {
            "display_uom": self.env.user.has_group("uom.group_uom"),
            "order_id": self.id,
            "product_catalog_order_model": self._name,
        }

    def _is_readonly(self):
        return False

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        return 0
