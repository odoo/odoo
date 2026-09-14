from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductValue(models.Model):
    _name = "product.value"
    _description = "Product Value"
    _order = "date desc, id desc"

    product_id = fields.Many2one(
        comodel_name="product.product",
        index=True,
    )
    lot_id = fields.Many2one(comodel_name="stock.lot")
    move_id = fields.Many2one(
        comodel_name="stock.move",
        index="btree_not_null",
    )

    value = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
    )
    date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        required=True,
    )

    description = fields.Char()

    current_value = fields.Monetary(
        related="move_id.value",
        string="Current Value",
        currency_field="currency_id",
    )
    current_value_details = fields.Char(compute="_compute_current_value_details")
    current_value_description = fields.Text(compute="_compute_value_description")
    computed_value_description = fields.Text(compute="_compute_value_description")

    @api.depends("move_id", "lot_id", "product_id")
    def _compute_company_id(self):
        for product_value in self:
            if product_value.move_id:
                product_value.company_id = product_value.move_id.company_id
            elif product_value.lot_id:
                product_value.company_id = product_value.lot_id.company_id
            elif product_value.product_id:
                product_value.company_id = product_value.product_id.company_id
            else:
                product_value.company_id = self.env.company

    @api.depends("move_id.value", "move_id.move_line_ids.quantity_product_uom")
    def _compute_current_value_details(self):
        _debug.perf.count("manual_valuation_details", values=self)
        for product_value in self:
            move = product_value.move_id
            quantity = move._get_valued_qty() if move else 0
            if not (move and quantity):
                product_value.current_value_details = False
                continue
            uom = move.product_id.uom_id.name
            price_unit = move.value / quantity
            product_value.current_value_details = _(
                "For %(quantity)s %(uom)s (%(price_unit)s per %(uom)s)",
                quantity=quantity,
                uom=uom,
                price_unit=price_unit,
            )

    @api.depends("move_id.value_justification", "move_id.value_computed_justification")
    def _compute_value_description(self):
        for product_value in self:
            if not product_value.move_id:
                product_value.current_value_description = False
                product_value.computed_value_description = False
                continue
            product_value.current_value_description = (
                product_value.move_id.value_justification
            )
            product_value.computed_value_description = (
                product_value.move_id.value_computed_justification
            )

    @api.model_create_multi
    def create(self, vals_list):
        _debug.lifecycle("manual_valuation_create", count=len(vals_list))
        product_ids = set()
        move_ids = set()
        lot_ids = set()

        records_a_price_already_set = self.env.context.get("disable_auto_revaluation")
        for vals in vals_list:
            if vals.get("move_id"):
                move_ids.add(vals["move_id"])
            elif vals.get("lot_id") and vals.get("product_id"):
                product_ids.add(vals["product_id"])
                if not records_a_price_already_set:
                    lot_ids.add(vals["lot_id"])
            elif vals.get("product_id") and not records_a_price_already_set:
                product_ids.add(vals["product_id"])

        res = super().create(vals_list)
        if move_ids:
            self.env["stock.move"].browse(move_ids)._set_value()
        if product_ids:
            self.env["product.product"].browse(product_ids)._update_standard_price()
        if lot_ids:
            self.env["stock.lot"].browse(lot_ids).sudo()._update_standard_price()
        return res
