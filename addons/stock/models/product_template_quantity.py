from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import DOMAIN_PREDICATES

from ..tools import debug_log as dbg
from odoo.addons.stock.const import TEMPLATE_QUANTITY_FIELDS
from odoo.addons.stock.tools.quantity import get_domain_quantity_in_python


class ProductTemplateQuantity(models.Model):
    _inherit = "product.template"

    @api.depends(
        "product_variant_ids.qty_available",
        "product_variant_ids.qty_available_virtual",
        "product_variant_ids.qty_incoming",
        "product_variant_ids.qty_outgoing",
    )
    @api.depends_context(
        "lot_id",
        "owner_id",
        "owners",
        "package_id",
        "from_date",
        "to_date",
        "location",
        "warehouse_id",
        "search_location",
        "search_warehouse",
        "allowed_company_ids",
        "uid",
        "strict",
        "skip_in_progress",
    )
    def _compute_quantities(self):
        res = self._aggregate_variant_quantities()
        for template in self.with_context(skip_qty_available_update=True):
            template.update(res[template.id])

    @dbg.timed
    def _aggregate_variant_quantities(self):
        self.product_variant_ids._origin.fetch(TEMPLATE_QUANTITY_FIELDS)
        dbg.performance.debug(
            "_aggregate_variant_quantities: %d templates, %d variants",
            len(self),
            len(self.product_variant_ids),
        )
        prod_available = {}
        for template in self:
            variants = template.product_variant_ids._origin
            prod_available[template.id] = {
                fname: sum(variants.mapped(fname)) for fname in TEMPLATE_QUANTITY_FIELDS
            }
        return prod_available

    def _get_domain_variant_quantity(self, field_name, operator, value):
        Product = self.env["product.product"]
        operation = DOMAIN_PREDICATES.get(operator)
        if operation is None:
            return get_domain_quantity_in_python(self, field_name, operator, value)

        variant_totals, candidates = Product._get_quantity_totals(field_name)
        totals = defaultdict(float)
        for variant in candidates.filtered("active"):
            totals[variant.product_tmpl_id.id] += variant_totals[variant.id]
        return Product._get_domain_quantity_search(
            totals, operation, operator, value, field_name
        )

    def _search_qty_available(self, operator, value):
        return self._get_domain_variant_quantity("qty_available", operator, value)

    def _search_qty_available_virtual(self, operator, value):
        return self._get_domain_variant_quantity(
            "qty_available_virtual", operator, value
        )

    def _search_qty_incoming(self, operator, value):
        return self._get_domain_variant_quantity("qty_incoming", operator, value)

    def _search_qty_outgoing(self, operator, value):
        return self._get_domain_variant_quantity("qty_outgoing", operator, value)

    def _inverse_qty_available(self):
        if self.env.context.get("skip_qty_available_update", False):
            return
        self._update_qty_available([template.qty_available for template in self])

    def _check_qty_available_update(self, quantities):
        for template, qty in zip(self, quantities, strict=True):
            if template.type != "consu" or not template.is_storable:
                raise UserError(
                    _(
                        "%(product)s does not track inventory, so it cannot have a"
                        " quantity on hand. Enable Track Inventory first.",
                        product=template.display_name,
                    ),
                )
            if template.tracking != "none":
                raise UserError(
                    _(
                        "%(product)s is tracked by lot/serial number: set its quantity"
                        " through an inventory adjustment so lot/serial numbers can be"
                        " assigned.",
                        product=template.display_name,
                    ),
                )
            if template.product_variant_count > 1:
                raise UserError(
                    _(
                        "%(product)s has several variants: update the quantity of each"
                        " variant instead.",
                        product=template.display_name,
                    ),
                )
            if not template.product_variant_id:
                if template.id:
                    raise UserError(
                        _(
                            "%(product)s has no active variant, so there is nothing"
                            " to hold a quantity on hand. Unarchive a variant first.",
                            product=template.display_name,
                        ),
                    )
                raise UserError(
                    _("Save the product form before updating the Quantity On Hand."),
                )
            if template.uom_id.compare(qty, 0) < 0:
                raise UserError(
                    _(
                        "The quantity on hand of %(product)s cannot be set to a negative value.",
                        product=template.display_name,
                    ),
                )

    def _update_qty_available(self, quantities):
        template_ids = []
        quantities_to_apply = []
        for template, qty in zip(self, quantities, strict=True):
            if not qty and (template.type != "consu" or not template.is_storable):
                continue
            template_ids.append(template.id)
            quantities_to_apply.append(qty)
        if not template_ids:
            return
        templates_to_apply = self.browse(template_ids)
        dbg.pipeline.debug(
            "template _update_qty_available -> variants of %s",
            dbg.rec(templates_to_apply),
        )
        templates_to_apply._check_qty_available_update(quantities_to_apply)
        templates_to_apply.product_variant_id._update_qty_available(quantities_to_apply)
