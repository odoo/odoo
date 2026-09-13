import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _prepare_quantities_vals(self, filters, location_domains=None):
        return super(
            ProductProduct,
            self.with_context(with_expiration=fields.Datetime.now()),
        )._prepare_quantities_vals(filters, location_domains=location_domains)

    @api.depends_context("with_expiration", "fresh_qty_forecast")
    @api.depends("stock_quant_ids.removal_date")
    def _compute_quantities(self):
        return super()._compute_quantities()

    def _get_expiration_date_from(self, from_date=None):
        if not self.use_expiration_date:
            return False
        self.check_singleton()
        from_date = from_date or fields.Datetime.today()
        return from_date + datetime.timedelta(days=self.expiration_time)

    def _get_expired_quant_domain_at_date(self, domain_quant, to_date):
        if not self.env.context.get("with_expiration"):
            return None
        max_date = (
            to_date
            if to_date and self.env.context.get("fresh_qty_forecast")
            else self.env.context["with_expiration"]
        )
        return domain_quant & Domain([("removal_date", "<=", max_date)])

    qty_free = fields.Float(
        help="Available quantity (computed as Quantity On Hand "
        "- reserved quantity - quantity to remove)\n"
        "In a context with a single Stock Location, this includes "
        "goods stored in this location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods stored in the Stock Location of this Warehouse, or any "
        "of its children.\n"
        "Otherwise, this includes goods stored in any Stock Location "
        "with 'internal' type."
    )

    qty_available_virtual = fields.Float(
        help="Forecast quantity (computed as Quantity On Hand "
        "- Outgoing + Incoming - Quantity to Remove)\n"
        "In a context with a single Stock Location, this includes "
        "goods stored in this location, or any of its children.\n"
        "In a context with a single Warehouse, this includes "
        "goods stored in the Stock Location of this Warehouse, or any "
        "of its children.\n"
        "Otherwise, this includes goods stored in any Stock Location "
        "with 'internal' type."
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends_context("with_expiration", "fresh_qty_forecast")
    def _compute_quantities(self):
        return super()._compute_quantities()

    use_expiration_date = fields.Boolean(
        compute="_compute_use_expiration_date",
        store=True,
        readonly=False,
        help="When this box is ticked, you have the possibility to specify dates to manage"
        " product expiration, on the product and on the corresponding lot/serial numbers."
        " Defaults to the product category setting.",
    )
    expiration_time = fields.Integer(
        string="Expiration Date",
        help="Number of days after the receipt of the products (from the vendor"
        " or in stock after production) after which the goods may become dangerous"
        " and must not be consumed. It will be computed on the lot/serial number.",
    )
    use_time = fields.Integer(
        string="Best Before Date",
        help="Number of days before the Expiration Date after which the goods starts"
        " deteriorating, without being dangerous yet. It will be computed on the lot/serial number.",
    )
    removal_time = fields.Integer(
        string="Removal Date",
        help="Number of days before the Expiration Date after which the goods"
        " should be removed from the stock and not be counted in the Fresh On Hand Stock anymore."
        "It will be computed on the lot/serial number.",
    )
    alert_time = fields.Integer(
        string="Alert Date",
        help="Number of days before the Expiration Date after which an alert should be"
        " raised on the lot/serial number. It will be computed on the lot/serial number.",
    )

    @api.constrains("expiration_time", "use_time", "removal_time", "alert_time")
    def _check_expiry_times(self):
        for template in self:
            offsets = {
                self.env._("Expiration Date"): template.expiration_time,
                self.env._("Best Before Date"): template.use_time,
                self.env._("Removal Date"): template.removal_time,
                self.env._("Alert Date"): template.alert_time,
            }
            negative = [name for name, days in offsets.items() if days < 0]
            if negative:
                raise ValidationError(
                    self.env._(
                        "The expiry delays of %(product)s are numbers of days and cannot"
                        " be negative: %(fields)s. A negative delay puts a lot's removal"
                        " date after its expiration date, which leaves expired goods"
                        " reservable and blocks the transfer that would clear them.",
                        product=template.display_name,
                        fields=", ".join(negative),
                    )
                )

    @api.depends("categ_id.use_expiration_date")
    def _compute_use_expiration_date(self):
        for product in self:
            product.use_expiration_date = (
                product.tracking != "none" and product.categ_id.use_expiration_date
            )

    def write(self, vals):
        if vals.get("tracking") == "none":
            vals["use_expiration_date"] = False
            reactivated = self.browse()
        elif (
            vals.get("tracking") not in (None, "none")
            and "use_expiration_date" not in vals
        ):
            # `tracking` isn't itself a dependency of `_compute_use_expiration_date`
            # (it gets recomputed by `stock` on every `is_storable` write, which
            # would otherwise clobber a manual override on an unrelated write) —
            # force a recompute only on an actual none -> tracked transition.
            reactivated = self.filtered(lambda p: p.tracking == "none")
        else:
            reactivated = self.browse()
        result = super().write(vals)
        if reactivated:
            self.env.add_to_compute(self._fields["use_expiration_date"], reactivated)
        return result
