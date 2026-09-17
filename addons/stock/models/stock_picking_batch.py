from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from ..tools import debug_log as dbg


class StockPickingBatch(models.Model):
    _name = "stock.picking.batch"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.stock.consignment"]
    _description = "Batch Transfer"
    _order = "name desc"

    name = fields.Char(
        string="Batch Transfer",
        default="New",
        copy=False,
        readonly=True,
        required=True,
    )
    description = fields.Char()
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        check_company=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        readonly=True,
        required=True,
    )
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="batch_id",
        string="Transfers",
        domain="[('id', 'in', allowed_picking_ids)]",
        check_company=True,
        help="List of transfers associated to this batch",
    )
    show_check_availability = fields.Boolean(compute="_compute_show_check_availability")
    show_allocation = fields.Boolean(
        string="Show Allocation Button",
        compute="_compute_show_allocation",
    )
    allowed_picking_ids = fields.One2many(
        comodel_name="stock.picking",
        compute="_compute_allowed_picking_ids",
    )
    move_ids = fields.One2many(
        comodel_name="stock.move",
        string="Stock moves",
        compute="_compute_move_ids",
    )
    move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        string="Stock move lines",
        compute="_compute_move_line_ids",
        inverse="_inverse_move_line_ids",
        search="_search_move_line_ids",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        compute="_compute_state",
        default="draft",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        required=True,
        tracking=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        index=True,
        copy=False,
        check_company=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        related="picking_type_id.warehouse_id",
    )
    picking_type_code = fields.Selection(related="picking_type_id.code")
    date_planned = fields.Datetime(
        string="Scheduled Date",
        compute="_compute_date_planned",
        store=True,
        copy=False,
        readonly=False,
        help="""Scheduled date for the transfers to be processed.
              - If manually set then scheduled date for all transfers in batch will automatically update to this date.
              - If not manually changed and transfers are added/removed/updated then this will be their earliest scheduled date
                but this scheduled date will not be set for all transfers in batch.""",
    )
    is_wave = fields.Boolean(string="This batch is a wave")
    wave_product_id = fields.Many2one(
        comodel_name="product.product",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
    )
    wave_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Wave Product Category",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
    )
    wave_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Wave Contact",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
    )
    wave_country_id = fields.Many2one(
        comodel_name="res.country",
        string="Wave Destination Country",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
    )
    wave_source_location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
    )
    wave_dest_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Wave Destination Location",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
    )
    wave_location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
        domain="[('id', 'in', picking_type_id.wave_location_ids)]",
        help="One of the operation type's wave locations. An empty wave declaring "
        "its grouping values here is filled by automatic waving; once it holds "
        "lines, the values are read from them.",
    )
    show_lots_text = fields.Boolean(compute="_compute_show_lots_text")
    estimated_shipping_weight = fields.Float(
        digits="Product Unit",
        compute="_compute_estimated_shipping_capacity",
    )
    estimated_shipping_volume = fields.Float(
        digits="Product Unit",
        compute="_compute_estimated_shipping_capacity",
    )
    properties = fields.Properties(
        definition="picking_type_id.batch_properties_definition",
        copy=True,
    )

    @api.depends("description")
    @api.depends_context("add_to_existing_batch")
    def _compute_display_name(self):
        if not self.env.context.get("add_to_existing_batch"):
            return super()._compute_display_name()
        for batch in self:
            batch.display_name = (
                f"{batch.name}: {batch.description}"
                if batch.description
                else batch.name
            )
        return None

    @api.depends("picking_ids.show_lots_text")
    def _compute_show_lots_text(self):
        for batch in self:
            batch.show_lots_text = bool(batch.picking_ids[:1].show_lots_text)

    @api.depends(
        "picking_ids.move_ids.move_line_ids.quantity_product_uom",
        "picking_ids.move_ids.move_line_ids.product_id.weight",
        "picking_ids.move_ids.move_line_ids.product_id.volume",
        "picking_ids.move_ids.move_line_ids.result_package_id.shipping_weight",
        "picking_ids.move_ids.move_line_ids.result_package_id.package_type_id",
        "picking_ids.move_ids.move_line_ids.result_package_id.package_type_id.base_weight",
        "picking_ids.move_ids.move_line_ids.result_package_id.package_type_id.packaging_length",
        "picking_ids.move_ids.move_line_ids.result_package_id.package_type_id.width",
        "picking_ids.move_ids.move_line_ids.result_package_id.package_type_id.height",
    )
    def _compute_estimated_shipping_capacity(self):
        for batch in self:
            estimated_shipping_weight = 0
            estimated_shipping_volume = 0
            weighed_package_ids = set()
            measured_package_ids = set()
            move_lines = batch.move_line_ids
            for pack in move_lines.result_package_id:
                package_type = pack.package_type_id
                if pack.shipping_weight:
                    estimated_shipping_weight += pack.shipping_weight
                    weighed_package_ids.add(pack.id)
                elif package_type:
                    estimated_shipping_weight += package_type.base_weight or 0
                if package_type:
                    estimated_shipping_volume += (
                        package_type.packaging_length
                        * package_type.width
                        * package_type.height
                    ) / 1000.0**3
                    measured_package_ids.add(pack.id)
            for move_line in move_lines:
                package_id = move_line.result_package_id.id
                if package_id not in weighed_package_ids:
                    estimated_shipping_weight += (
                        move_line.product_id.weight * move_line.quantity_product_uom
                    )
                if package_id not in measured_package_ids:
                    estimated_shipping_volume += (
                        move_line.product_id.volume * move_line.quantity_product_uom
                    )
            batch.estimated_shipping_weight = estimated_shipping_weight
            batch.estimated_shipping_volume = estimated_shipping_volume

    def _get_domain_allowed_picking(self):
        self.check_singleton()
        states = ["waiting", "confirmed", "assigned"]
        if self.state == "draft":
            states.append("draft")
        domain = Domain("company_id", "=", self.company_id.id) & Domain(
            "state", "in", states
        )
        if self.picking_type_id:
            domain &= Domain("picking_type_id", "=", self.picking_type_id.id)
        return domain

    @api.depends("company_id", "picking_type_id", "state")
    def _compute_allowed_picking_ids(self):
        grouped = self.grouped(
            lambda batch: (
                batch.company_id,
                batch.picking_type_id,
                batch.state == "draft",
            )
        )
        for batches in grouped.values():
            batches.allowed_picking_ids = self.env[
                "stock.picking"
            ].search(  # noqa: E8507 - one query per distinct (company, type, draft); batches sharing one were merged above
                batches[:1]._get_domain_allowed_picking()
            )

    @api.depends(
        "picking_ids",
        "picking_ids.move_line_ids",
        "picking_ids.move_ids",
        "picking_ids.move_ids.state",
    )
    def _compute_move_ids(self):
        for batch in self:
            batch.move_ids = batch.picking_ids.move_ids

    @api.depends(
        "picking_ids",
        "picking_ids.move_line_ids",
        "picking_ids.move_ids",
        "picking_ids.move_ids.state",
    )
    def _compute_show_check_availability(self):
        for batch in self:
            batch.show_check_availability = any(
                m.state not in ["assigned", "done", "cancel"] for m in batch.move_ids
            )

    @api.depends(
        "picking_ids.move_line_ids.product_id",
        "picking_ids.move_line_ids.product_id.categ_id",
        "picking_ids.move_line_ids.location_id",
        "picking_ids.partner_id",
        "picking_ids.partner_id.country_id",
        "picking_ids.location_id",
        "picking_ids.location_dest_id",
    )
    def _compute_wave_grouping(self):
        criteria = self.env["stock.picking.type"]._get_grouping_criteria()
        for batch in self:
            if not batch.move_line_ids:
                for criterion in criteria.values():
                    if criterion.wave_field:
                        batch[criterion.wave_field] = batch[criterion.wave_field]
                batch.wave_location_id = batch.wave_location_id
                continue
            for criterion in criteria.values():
                if criterion.wave_field:
                    value = batch.mapped(criterion.batch_path)
                    batch[criterion.wave_field] = value if len(value) == 1 else False
            picking_type = batch.picking_type_id
            nearest = {
                picking_type._get_nearest_wave_location(location)
                for location in batch.move_line_ids.location_id
                if picking_type
            }
            batch.wave_location_id = nearest.pop() if len(nearest) == 1 else False

    @api.depends("picking_ids", "picking_ids.move_line_ids")
    def _compute_move_line_ids(self):
        for batch in self:
            batch.move_line_ids = batch.picking_ids.move_line_ids

    def _search_move_line_ids(self, operator, value):
        return [("picking_ids.move_line_ids", operator, value)]

    @api.depends("state", "move_ids", "picking_type_id")
    @api.depends_context("uid")
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.env.user.has_group("stock.group_reception_report"):
            return
        for batch in self:
            batch.show_allocation = batch.picking_ids._is_allocation_shown(
                batch.picking_type_id
            )

    @api.depends("picking_ids", "picking_ids.state")
    def _compute_state(self):
        batchs = self.filtered(lambda batch: batch.state not in ["done", "cancel"])
        for batch in batchs:
            if not batch.picking_ids:
                if batch.state == "in_progress":
                    batch.state = "cancel"
                continue
            if all(picking.state == "cancel" for picking in batch.picking_ids):
                dbg.lifecycle.debug(
                    "[batch:%s] all pickings cancelled -> cancel", batch.id
                )
                batch.state = "cancel"
            elif all(
                picking.state in ["done", "cancel"] for picking in batch.picking_ids
            ):
                dbg.lifecycle.debug("[batch:%s] all pickings closed -> done", batch.id)
                batch.state = "done"

    @api.depends("picking_ids", "picking_ids.date_planned")
    def _compute_date_planned(self):
        for rec in self:
            rec.date_planned = min(
                rec.picking_ids.filtered("date_planned").mapped("date_planned"),
                default=False,
            )

    def _inverse_move_line_ids(self):
        for batch in self:
            new_move_lines = batch.move_line_ids
            for picking in batch.picking_ids:
                old_move_lines = picking.move_line_ids
                picking.move_line_ids = new_move_lines.filtered(
                    lambda ml, picking=picking: ml.picking_id.id == picking.id
                )
                move_lines_to_unlink = old_move_lines - new_move_lines
                if move_lines_to_unlink:
                    dbg.logic.debug(
                        "[batch:%s] _inverse_move_line_ids unlinks %s of picking %s",
                        batch.id,
                        dbg.rec(move_lines_to_unlink),
                        picking.id,
                    )
                    move_lines_to_unlink.unlink()

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.picking.batch.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                company_id = vals.get("company_id", self.env.company.id)
                picking_type = self.env["stock.picking.type"].browse(
                    vals.get("picking_type_id")
                )
                if picking_type:
                    sequence_code = (
                        "picking.wave" if vals.get("is_wave") else "picking.batch"
                    )
                    vals["name"] = self._prepare_name(
                        picking_type, sequence_code, company_id
                    )
        return super().create(vals_list)

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.picking.batch.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        batches_to_rename = self.env["stock.picking.batch"]
        if vals.get("picking_type_id"):
            picking_type = self.env["stock.picking.type"].browse(
                vals.get("picking_type_id")
            )
            batches_to_rename = self.filtered(
                lambda b: b.picking_type_id != picking_type
            )
        res = super().write(vals)
        if vals.get("picking_type_id"):
            self._check_pickings_are_allowed()
            for batch in batches_to_rename:
                sequence_code = "picking.wave" if batch.is_wave else "picking.batch"
                batch.name = self._prepare_name(
                    picking_type, sequence_code, batch.company_id
                )
        if vals.get("picking_ids"):
            self._update_picking_type_from_pickings()
        if "user_id" in vals:
            self.picking_ids.update_batch_user(vals["user_id"])
        if vals.get("date_planned"):
            self.picking_ids.filtered(
                lambda picking: picking.date_planned != self.date_planned
            ).date_planned = vals["date_planned"]
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if any(batch.state == "done" for batch in self):
            raise UserError(_("You cannot delete Done batch transfers."))

    @dbg.timed
    def action_confirm(self):
        self.check_singleton()
        if not self.picking_ids:
            raise UserError(_("You have to set some pickings to batch."))
        dbg.pipeline.debug(
            "[batch:%s] action_confirm -> %s", self.id, dbg.rec(self.picking_ids)
        )
        self.picking_ids.action_confirm()
        self._check_company()
        self.state = "in_progress"
        return True

    def action_cancel(self):
        dbg.lifecycle.debug(
            "action_cancel: %s -> cancel, detaching %s",
            dbg.rec(self),
            dbg.rec(self.picking_ids),
        )
        self.state = "cancel"
        self.picking_ids = False
        return True

    @dbg.timed
    def action_done(self):
        def has_no_quantity(picking):
            return all(
                not m.picked or m.product_uom_id.is_zero(m.quantity)
                for m in picking.move_ids
                if m.state not in ("done", "cancel")
            )

        def is_empty(picking):
            return all(
                m.product_uom_id.is_zero(m.quantity)
                for m in picking.move_ids
                if m.state not in ("done", "cancel")
            )

        self.check_singleton()
        self._check_company()
        pickings = self.picking_ids.filtered(
            lambda picking: picking.state not in ("done", "cancel")
        )
        empty_waiting_pickings = self.picking_ids.filtered(
            lambda p: (
                (p.state in ("waiting", "confirmed") and has_no_quantity(p))
                or (p.state == "assigned" and is_empty(p))
            )
        )
        pickings -= empty_waiting_pickings
        if not pickings:
            raise UserError(
                _("No quantity was processed in any transfer of this batch.")
            )

        empty_pickings = pickings.filtered(has_no_quantity)

        pickings._check_before_validation()
        context = {
            "skip_validation_check": True,
            "pickings_to_detach": empty_waiting_pickings.ids,
            "batches_to_validate": self.ids,
        }
        if empty_pickings != pickings:
            pickings -= empty_pickings
            context["pickings_to_detach"] += empty_pickings.ids
        dbg.pipeline.debug(
            "[batch:%s] action_done: validate %s, detach %s",
            self.id,
            dbg.rec(pickings),
            context["pickings_to_detach"],
        )

        for picking in pickings:
            picking.message_post(
                body=Markup("<b>%s:</b> %s %s")
                % (_("Transferred by"), _("Batch Transfer"), self._get_html_link())
            )

        if empty_waiting_pickings:
            self.message_post(
                body=_(
                    "%s was removed from the batch, no quantity processed",
                    Markup(", ").join(
                        [picking._get_html_link() for picking in empty_waiting_pickings]
                    ),
                )
            )

        return pickings.with_context(**context).button_validate()

    def action_assign(self):
        self.check_singleton()
        dbg.pipeline.debug(
            "[batch:%s] action_assign -> %s", self.id, dbg.rec(self.picking_ids)
        )
        self.picking_ids.action_assign()

    def action_put_in_pack(
        self, *, package_id=False, package_type_id=False, package_name=False
    ):
        self.check_singleton()
        if self.state not in ("done", "cancel"):
            return self.move_line_ids.action_put_in_pack(
                package_id=package_id,
                package_type_id=package_type_id,
                package_name=package_name,
            )
        return None

    def action_view_reception_report(self):
        self.check_singleton()
        action = self.picking_ids[:1].action_view_reception_report()
        action["context"] = {"default_picking_ids": self.picking_ids.ids}
        return action

    def action_view_label_layout(self):
        if (
            self.env.user.has_group("stock.group_production_lot")
            and self.move_line_ids.lot_id
        ):
            view = self.env.ref("stock.picking_label_type_form")
            return {
                "name": _("Choose Type of Labels To Print"),
                "type": "ir.actions.act_window",
                "res_model": "picking.label.type",
                "views": [(view.id, "form")],
                "target": "new",
                "context": {"default_picking_ids": self.picking_ids.ids},
            }
        view = self.env.ref("stock.product_label_layout_form_picking")
        return {
            "name": _("Choose Labels Layout"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "product.label.layout",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": {
                "default_product_ids": self.move_line_ids.product_id.ids,
                "default_move_ids": self.move_ids.ids,
                "default_move_quantity": "move",
            },
        }

    def action_view_packages(self):
        self.check_singleton()
        if self.state == "done":
            return {
                "name": self.env._("Packages"),
                "res_model": "stock.package.history",
                "view_mode": "list",
                "views": [(False, "list")],
                "type": "ir.actions.act_window",
                "domain": [("picking_ids", "in", self.picking_ids.ids)],
                "context": {
                    "search_default_main_packages": True,
                },
            }

        return {
            "name": self.env._("Packages"),
            "res_model": "stock.package",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("stock.view_stock_package_list_editable").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "type": "ir.actions.act_window",
            "domain": [("picking_ids", "in", self.picking_ids.ids)],
            "context": {
                "picking_ids": self.picking_ids.ids,
                "location_id": self.picking_ids[:1].location_id.id,
                "can_add_entire_packs": self.picking_type_code != "incoming",
                "search_default_main_packages": True,
            },
        }

    @api.model
    def _prepare_name(self, picking_type, sequence_code, company_id):
        sequence = (
            self.env["ir.sequence"].with_company(company_id).next_by_code(sequence_code)
            or "/"
        )
        # The operation type code goes right after the sequence root, never
        # right before the number: a dated prefix such as BATCH/26/09/ must
        # stay glued to its counter (BATCH/OUT/26/09/0001), not be split by
        # the code. A single-level prefix is cut exactly where it was before.
        sequence_root, separator, sequence_number = sequence.partition("/")
        if not separator:
            sequence_root, sequence_number = "", sequence
        parts = [sequence_root, picking_type.sequence_code, sequence_number]
        return "/".join(part for part in parts if part)

    def _get_consignment_pickings(self):
        return self.picking_ids

    def _update_picking_type_from_pickings(self):
        for batch in self.filtered(
            lambda batch: not batch.picking_type_id and batch.picking_ids
        ):
            dbg.logic.debug(
                "[batch:%s] picking type taken from first picking: %s",
                batch.id,
                batch.picking_ids[:1].picking_type_id.id,
            )
            batch.picking_type_id = batch.picking_ids[:1].picking_type_id

    def _check_pickings_are_allowed(self):
        for batch in self:
            erroneous_pickings = batch.picking_ids - batch.picking_ids.filtered_domain(
                batch._get_domain_allowed_picking()
            )
            if erroneous_pickings:
                raise UserError(
                    _(
                        "The following transfers cannot be added to batch transfer %(batch)s. "
                        "Please check their states and operation types.\n\n"
                        "Incompatibilities: %(incompatible_transfers)s",
                        batch=batch.name,
                        incompatible_transfers=erroneous_pickings.mapped("name"),
                    )
                )

    def _is_auto_mergeable(self, *, moves=0, pickings=0, weight=0.0):
        self.check_singleton()
        picking_type = self.picking_type_id
        if (
            moves
            and picking_type.batch_max_lines
            and len(self.move_ids) + moves > picking_type.batch_max_lines
        ):
            dbg.logic.debug(
                "[batch:%s] not mergeable: %d + %d lines > %d",
                self.id,
                len(self.move_ids),
                moves,
                picking_type.batch_max_lines,
            )
            return False
        mergeable = not (
            pickings
            and picking_type.batch_max_pickings
            and len(self.picking_ids) + pickings > picking_type.batch_max_pickings
        )
        if not mergeable:
            dbg.logic.debug(
                "[batch:%s] not mergeable: %d + %d pickings > %d",
                self.id,
                len(self.picking_ids),
                pickings,
                picking_type.batch_max_pickings,
            )
        return mergeable

    def _prepare_merged_batch_vals(self):
        self.check_singleton()
        return {"user_id": self.user_id.id, "description": self.description}

    def _get_auto_wave_grouping_key(self, picking_type, nearest_parent_location):
        self.check_singleton()
        has_lines = bool(self.move_line_ids)
        values = []
        for criterion in picking_type._get_active_wave_criteria().values():
            if has_lines:
                values.append(self.mapped(criterion.batch_path))
            elif criterion.wave_field:
                values.append(self[criterion.wave_field])
            else:
                values.append(None)
        return (self.company_id, *values, nearest_parent_location)
