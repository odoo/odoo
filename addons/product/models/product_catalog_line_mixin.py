# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductCatalogLineMixin(models.AbstractModel):
    _name = "product.catalog.line.mixin"
    _description = "Product Catalog Line Mixin"

    product_id = fields.Many2one(comodel_name="product.product")

    def _get_product_catalog_lines_data(self, parent_record, **kwargs) -> dict:
        """Compute the additional product data according to the existing line details.

        Note: Self can be a multi-records recordset, all sharing the same product.
        """
        self.product_id.ensure_one()
        quantity_field = self._get_quantity_field()
        catalog_uom = self._get_product_uom()

        return {
            **parent_record._get_product_catalog_uom_data(self.product_id, uom=catalog_uom),
            "readOnly": parent_record._is_readonly() or len(self) > 1,
            "quantity": sum(
                self.mapped(
                    lambda line: line._get_product_uom()._compute_quantity(
                        qty=line[quantity_field], to_unit=catalog_uom
                    )
                )
            ),
            "price": self._get_catalog_unit_price(parent_record, **kwargs),
        }

    def _consider_in_catalog(self, parent_record, **kwargs) -> bool:  # noqa: ARG002
        """Determine whether the current line has to be considered in the catalog quantities."""
        self.ensure_one()
        return self.product_id and self.product_id.type != "combo"

    @api.model
    def _get_quantity_field(self) -> str:
        """Determine the field used to store the quantity on the catalog lines.

        Must be overridden in inheriting models.

        Note: this field is also the one used to update catalog quantities.
        """
        raise NotImplementedError

    @api.model
    def _get_product_uom_field(self) -> str:
        """Determine the field used to store the unit of measure on the catalog lines.

        Must be overridden in inheriting models.

        Note: this field is also the one used to update the catalog unit of measure.
        """
        raise NotImplementedError

    def _get_product_uom(self):
        """Determine the uom used to display (and compute) quantities in the catalog.

        Note: Self can be a multi-records recordset.
        """
        uom_field = self._get_product_uom_field()
        uoms = self[uom_field]
        if len(uoms) == 1:
            return uoms

        return self.product_id.uom_id

    def _update_catalog_quantity(self, quantity: float, uom, **kwargs) -> float:  # noqa: ARG002
        """Update the quantity (and uom) of the given line."""
        self.ensure_one()

        write_vals = {self._get_quantity_field(): quantity}

        uom_field = self._get_product_uom_field()
        if uom.id != self[uom_field].id:
            write_vals[uom_field] = uom.id

        self.write(write_vals)

    def _get_catalog_unit_price(self, parent_record, **kwargs) -> float:  # noqa: ARG002
        """Compute the product unit price in the catalog.

        Note: Self can be a multi-records recordset.
        """
        price_type = parent_record._get_product_price_type()
        if not price_type:
            return 0.0

        product = self.product_id
        product.ensure_one()
        return product._price_compute(
            price_type, uom=self._get_product_uom(), currency=parent_record._get_catalog_currency()
        )[product.id]

    def _can_be_unlinked_from_catalog(self) -> bool:
        """Determine whether the current line can be deleted (if its quantity becomes zero)."""
        self.ensure_one()
        return True
