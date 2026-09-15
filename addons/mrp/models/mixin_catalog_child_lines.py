from odoo import api, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinCatalogChildLines(models.AbstractModel):
    _name = "mixin.catalog.child.lines"
    _description = "Catalog Lines Held In A Child Field"

    def _update_catalog_line_quantity(self, line, quantity, **kwargs):
        raise NotImplementedError

    def _prepare_new_catalog_line_vals(self, product_id, quantity, **kwargs):
        raise NotImplementedError

    @api.model
    def _get_catalog_line_price(self, product_id):
        return self.env["product.product"].browse(product_id).standard_price

    def _get_product_catalog_record_lines(
        self, product_ids, *, child_field=False, **kwargs
    ):
        if not child_field:
            return {}
        return (
            self[child_field]
            .filtered(lambda line: line.product_id.id in product_ids)
            .grouped("product_id")
        )

    def _update_order_line_info(
        self, product_id, quantity, *, child_field=False, **kwargs
    ):
        if not child_field:
            return 0
        line = self[child_field].filtered(
            lambda line: line.product_id.id == product_id
        )[:1]
        by = "ignored"  # debuglog
        if line:
            by = "updated" if quantity != 0 else "unlinked"  # debuglog
            if quantity != 0:
                self._update_catalog_line_quantity(line, quantity, **kwargs)
            else:
                line.unlink()
        elif quantity > 0:
            by = "created"  # debuglog
            self.write(
                {
                    child_field: [
                        Command.create(
                            self._prepare_new_catalog_line_vals(
                                product_id, quantity, **kwargs
                            )
                        )
                    ]
                }
            )
            self._update_catalog_line_quantity(
                self[child_field].filtered(
                    lambda line: line.product_id.id == product_id
                )[-1:],
                quantity,
                **kwargs,
            )
        _debug.logic(
            "catalog_line",
            record=self.id,
            model=self._name,
            product=product_id,
            quantity=quantity,
            by=by,
        )
        return self._get_catalog_line_price(product_id)
