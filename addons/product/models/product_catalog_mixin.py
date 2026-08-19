# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ProductCatalogMixin(models.AbstractModel):
    """This mixin allows one model to work with the product catalog. It assumes the model using this
    mixin has a O2M field to a model inheriting from the `product.catalog.line.mixin`.
    """

    _name = "product.catalog.mixin"
    _description = "Product Catalog Mixin"

    @api.readonly
    def action_add_from_catalog(self) -> dict:
        self.ensure_one()
        kanban_view_id = self.env.ref("product.product_view_kanban_catalog").id
        search_view_id = self.env.ref("product.product_view_search_catalog").id
        additional_context = self._get_action_add_from_catalog_extra_context()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Products"),
            "res_model": "product.product",
            "views": [(kanban_view_id, "kanban"), (False, "form")],
            "search_view_id": [search_view_id, "search"],
            "domain": self._get_product_catalog_domain(),
            "context": {**self.env.context, **additional_context},
        }

    def _get_action_add_from_catalog_extra_context(self) -> dict:
        if not (child_field := self.env.context.get("child_field")):
            raise ValidationError(self.env._("Catalog missing the child field to update."))
        if child_field not in self._fields:
            raise ValidationError(self.env._("Wrong catalog child field!"))
        return {
            "product_catalog_order_id": self.id,
            "product_catalog_order_model": self._name,
            "product_catalog_currency_id": self._get_catalog_currency().id,
        }

    def _get_catalog_currency(self):
        return self.env.company.currency_id

    def _get_product_catalog_domain(self) -> Domain:
        """Determine the domain to search for products in the catalog."""
        return (
            Domain("company_id", "=", False) | Domain("company_id", "parent_of", self.company_id.id)
        ) & Domain("type", "!=", "combo")

    def _get_product_catalog_order_line_info(self, product_ids: list, **kwargs) -> dict:
        """Return products information to be shown in the catalog.

        Combines default product data from :meth:`_get_product_catalog_order_data` to the data
        of existing catalog lines (:meth:`_get_product_catalog_lines_data`).

        :param list product_ids: The products currently displayed in the product catalog, as a list
                                 of `product.product` ids.
        :param dict kwargs: additional values given for inherited models.
        """
        products = self.env["product.product"].browse(product_ids)

        catalog_data = self._get_product_catalog_order_data(products, **kwargs)
        lines_by_product = self._get_product_catalog_record_lines(product_ids, **kwargs)

        for product, lines in lines_by_product.items():
            catalog_data[product.id] = {
                **catalog_data[product.id],
                **lines._get_product_catalog_lines_data(parent_record=self, **kwargs),
            }

        return catalog_data

    def _get_product_catalog_order_data(self, products, **kwargs) -> dict:
        """Return the products base catalog data.

        This data is superseded by the lines data obtained through
        :meth:`_get_product_catalog_lines_data`.

        Note: this method allows to batch data computation for all the displayed catalog
        products, whereas :meth:`_get_product_catalog_product_data` provides product-specific
        data.

        :param products: The products currently displayed in the product catalog, as a
                         `product.product` recordset.
        :param dict kwargs: additional values forwarded to called methods.
        """
        res = {}

        default_prices = self._get_default_prices(products, **kwargs)
        catalog_is_readonly = bool(self and self._is_readonly())
        for product in products:
            res[product.id] = {
                "quantity": 0,
                **({"readOnly": True} if catalog_is_readonly else {}),
                **({"price": default_prices[product.id]} if product.id in default_prices else {}),
                **self._get_product_catalog_product_data(product, **kwargs),
            }

        return res

    def _get_default_prices(self, products, uom=None, **kwargs) -> dict:  # noqa: ARG002
        if (
            not self
            or not self._show_prices()
            or not (price_type := self._get_product_price_type())
        ):
            return {}

        return products._price_compute(price_type, uom=uom, currency=self._get_catalog_currency())

    def _is_readonly(self) -> bool:
        """Determine whether the current record can be updated."""
        self.ensure_one()
        return False

    def _show_prices(self) -> bool:
        return True

    def _get_product_price_type(self) -> str:
        """Specify the price type that should be computed as product 'price' in the catalog."""
        self.ensure_one()
        return "list_price"

    def _get_product_catalog_product_data(self, product, **kwargs) -> dict:
        """Return a product base data.

        :param product: The product, as a `product.product` record.
        :param dict kwargs: additional values forwarded to called methods.
        """
        return {
            "code": product.code or "",
            **self._get_product_catalog_uom_data(product, product.uom_id, **kwargs),
        }

    def _get_product_catalog_uom_data(self, product, uom, **kwargs) -> dict:  # noqa: ARG002
        """Return a product uom data.

        :param product: The product, as a `product.product` record.
        :param uom: The uom, as a `uom.uom` record.
        :param dict kwargs: additional values available for overrides.
        """
        if not self.env["res.groups"]._is_feature_enabled("uom.group_uom"):
            return {}

        return {
            "availableUoms": product._get_available_uoms().read(["display_name", "factor"]),
            "uomId": uom.id,
            "productUomId": product.uom_id.id,
        }

    def _get_product_catalog_record_lines(self, product_ids, child_field, **kwargs) -> dict:
        """Return the record's lines grouped by product.

        :param list product_ids: The products currently displayed in the product catalog, as a list
                                 of `product.product` ids.
        :param str child_field: name of the one2many field holding the catalog lines.
        """
        lines_to_consider = self[child_field].filtered(
            lambda child: (
                child.product_id.id in product_ids
                and child._consider_in_catalog(parent_record=self, **kwargs)
            )
        )
        return lines_to_consider.grouped("product_id")

    def _update_order_line_info(self, product, quantity, uom, child_field, **kwargs) -> dict:
        """Update the line information for a given product or create a new one if none exists yet.

        :param object product: recordset of `product.product`.
        :param float quantity: The product's quantity.
        :param object uom: recordset of `uom.uom`.
        :param str child_field: name of the one2many field holding the catalog lines.
        :param dict kwargs: additional values forwarded to called methods.

        :return: The updated product data.
        """
        self.ensure_one()
        if self._is_readonly():
            raise ValidationError(self.env._("You cannot add or remove products from this record."))

        product.ensure_one()
        existing_lines = self[child_field].filtered(
            lambda line: (
                line.product_id.id == product.id
                and line._consider_in_catalog(parent_record=self, **kwargs)
            )
        )
        catalog_line = existing_lines.browse()
        if existing_lines:
            if len(existing_lines) > 1:
                raise ValidationError(
                    self.env._(
                        "There are multiple lines with the same product, please update those one by"
                        " one and not through the catalog."
                    )
                )

            if quantity == 0 and existing_lines._can_be_unlinked_from_catalog():
                existing_lines.unlink()
                existing_lines = existing_lines.browse()
            else:
                catalog_line = existing_lines
                catalog_line._update_catalog_quantity(quantity, uom, **kwargs)

        elif quantity > 0:
            catalog_line = self._catalog_create_new_line(
                child_field, product, quantity, uom, **kwargs
            )

        return self._get_updated_order_line_info(catalog_line, product, uom, **kwargs)

    def _get_updated_order_line_info(self, catalog_line, product, uom, **kwargs) -> dict:
        """Return the updated product information to be shown in the catalog."""
        if self._show_prices():
            if catalog_line:
                price = catalog_line._get_catalog_unit_price(parent_record=self, **kwargs)
            else:
                price = self._get_product_catalog_default_unit_price(product, uom, **kwargs)

            return {'price': price}

        return {}

    def _catalog_create_new_line(self, child_field, product, quantity, uom, **kwargs):
        """Create a new product line according to the provided values."""
        self.ensure_one()

        return self.env[self._fields[child_field].comodel_name].create(
            self._catalog_prepare_new_line_vals(child_field, product, quantity, uom, **kwargs)
        )

    def _catalog_prepare_new_line_vals(self, child_field, product, quantity, uom, **kwargs) -> dict:  # noqa: ARG002
        """Prepare the data of the new product line according to the provided values."""
        Comodel = self.env[self._fields[child_field].comodel_name]
        return {
            self._fields[child_field].inverse_name: self.id,
            "product_id": product.id,
            Comodel._get_quantity_field(): quantity,
            Comodel._get_product_uom_field(): uom.id,
            "sequence": (self[child_field][-1:].sequence or 1) + 1,
        }

    def _get_product_catalog_default_unit_price(self, product, uom, **kwargs) -> float:  # noqa: ARG002
        return self._get_default_prices(product, uom=uom, **kwargs)[product.id]
