from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class StockQuantRelocate(models.TransientModel):
    _name = "stock.quant.relocate"
    _description = "Stock Quantity Relocation"

    quant_ids = fields.Many2many(comodel_name="stock.quant")
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
    )
    dest_location_id = fields.Many2one(
        comodel_name="stock.location",
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
    )
    dest_package_id_domain = fields.Char(compute="_compute_dest_package_id_domain")
    dest_package_id = fields.Many2one(
        comodel_name="stock.package",
        compute="_compute_dest_package_id",
        store=True,
        domain="dest_package_id_domain",
    )
    message = fields.Text(string="Reason for relocation")
    is_partial_package = fields.Boolean(compute="_compute_partial_packages")
    partial_package_names = fields.Char(compute="_compute_partial_packages")
    is_multi_location = fields.Boolean(compute="_compute_is_multi_location")

    @api.constrains("quant_ids")
    def _check_single_company(self):
        for wizard in self:
            if len(wizard.quant_ids.company_id) > 1:
                raise UserError(
                    self.env._(
                        "You cannot relocate quantities belonging to several"
                        " companies at once.",
                    ),
                )

    @api.depends("quant_ids")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.quant_ids.company_id[:1]

    @api.depends("quant_ids")
    def _compute_partial_packages(self):
        self.is_partial_package = False
        self.partial_package_names = ""
        for wizard in self:
            incomplete_packages = (
                wizard.quant_ids._filtered_breaking_a_package().package_id
            )
            if incomplete_packages:
                wizard.is_partial_package = True
                wizard.partial_package_names = ", ".join(
                    incomplete_packages.mapped("display_name")
                )

    @api.depends("dest_location_id", "quant_ids")
    def _compute_is_multi_location(self):
        self.is_multi_location = False
        for wizard in self:
            if len(wizard.quant_ids.location_id) > 1 and not wizard.dest_location_id:
                wizard.is_multi_location = True

    @api.depends("dest_location_id", "quant_ids")
    def _compute_dest_package_id_domain(self):
        for wizard in self:
            domain = [
                "|",
                ("company_id", "=", wizard.company_id.id),
                ("company_id", "=", False),
            ]
            if wizard.dest_location_id:
                domain += [
                    "|",
                    ("location_id", "=", False),
                    ("location_id", "=", wizard.dest_location_id.id),
                ]
            elif len(wizard.quant_ids.location_id) == 1:
                domain += [
                    "|",
                    ("location_id", "=", False),
                    ("location_id", "=", wizard.quant_ids.location_id.id),
                ]
            wizard.dest_package_id_domain = domain

    @api.depends("dest_package_id_domain")
    def _compute_dest_package_id(self):
        for wizard in self:
            if wizard.dest_package_id and not wizard.dest_package_id.search(
                [("id", "=", wizard.dest_package_id.id)]
                + literal_eval(wizard.dest_package_id_domain),
                limit=1,
            ):
                wizard.dest_package_id = False

    def action_relocate_quants(self):
        self.check_singleton()
        lot_ids = self.quant_ids.lot_id
        product_ids = self.quant_ids.product_id

        if not self.dest_location_id and not self.dest_package_id:
            dbg.logic.debug("action_relocate_quants: no destination, nothing done")
            return None
        dbg.pipeline.debug(
            "action_relocate_quants %s -> location %s package %s partial=%s",
            dbg.rec(self.quant_ids),
            self.dest_location_id.id,
            self.dest_package_id.id,
            self.is_partial_package,
        )
        self.quant_ids.action_clear_inventory_quantity()

        if self.is_partial_package and not self.dest_package_id:
            quants_to_unpack = self.quant_ids._filtered_breaking_a_package()
            quants_to_unpack.move_quants(
                location_dest_id=self.dest_location_id,
                message=self.message,
                unpack=True,
            )
            self.quant_ids -= quants_to_unpack
        self.quant_ids.move_quants(
            location_dest_id=self.dest_location_id,
            package_dest_id=self.dest_package_id,
            message=self.message,
        )

        if self.env.context.get("default_lot_id", False) and len(lot_ids) == 1:
            return lot_ids.action_lot_open_quants()
        elif self.env.context.get("single_product", False) and len(product_ids) == 1:
            return product_ids.action_view_quants()
        return self.quant_ids.with_context(always_show_loc=1).action_view_quants()
