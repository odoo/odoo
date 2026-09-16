# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class WizStockBarcodesRead(models.AbstractModel):
    _name = "wiz.stock.barcodes.read"
    _inherit = "barcodes.barcode_events_mixin"
    _description = "Wizard to read barcode"
    # To prevent remove the record wizard until 2 days old
    _transient_max_hours = 48
    _allowed_product_types = ["product", "consu"]

    barcode = fields.Char()
    res_model_id = fields.Many2one(comodel_name="ir.model", index=True)
    res_id = fields.Integer(index=True)
    product_id = fields.Many2one(
        comodel_name="product.product", domain=[("type", "in", _allowed_product_types)]
    )
    product_uom_id = fields.Many2one(comodel_name="uom.uom")
    product_tracking = fields.Selection(related="product_id.tracking", readonly=True)
    lot_id = fields.Many2one(comodel_name="stock.lot")
    lot_name = fields.Char(
        "Lot/Serial Number Name",
        compute="_compute_lot_name",
        readonly=False,
        store=True,
    )
    location_id = fields.Many2one(comodel_name="stock.location")
    location_dest_id = fields.Many2one(
        comodel_name="stock.location", string="Location dest."
    )
    packaging_id = fields.Many2one(comodel_name="product.packaging")
    product_packaging_ids = fields.One2many(related="product_id.packaging_ids")
    package_id = fields.Many2one(comodel_name="stock.quant.package")
    result_package_id = fields.Many2one(comodel_name="stock.quant.package")
    owner_id = fields.Many2one(comodel_name="res.partner")
    packaging_qty = fields.Float(string="Package Qty", digits="Product Unit of Measure")
    product_qty = fields.Float(digits="Product Unit of Measure")
    manual_entry = fields.Boolean(string="Manual", help="Entry manual data")
    confirmed_moves = fields.Boolean(
        string="Confirmed moves", related="option_group_id.confirmed_moves"
    )
    message_type = fields.Selection(
        [
            ("info", "Barcode read with additional info"),
            ("not_found", "No barcode found"),
            ("more_match", "More than one matches found"),
            ("success", "Barcode read correctly"),
        ],
        readonly=True,
    )
    message = fields.Char(readonly=True)
    message_step = fields.Char(readonly=True)
    guided_product_id = fields.Many2one(comodel_name="product.product")
    guided_location_id = fields.Many2one(comodel_name="stock.location")
    guided_location_dest_id = fields.Many2one(comodel_name="stock.location")
    guided_lot_id = fields.Many2one(comodel_name="stock.lot")
    action_ids = fields.Many2many(
        comodel_name="stock.barcodes.action", compute="_compute_action_ids"
    )
    option_group_id = fields.Many2one(comodel_name="stock.barcodes.option.group")
    visible_force_done = fields.Boolean()
    step = fields.Integer()
    is_manual_qty = fields.Boolean(compute="_compute_is_manual_qty")
    is_manual_confirm = fields.Boolean(compute="_compute_is_manual_qty")
    # Technical field to allow use in attrs
    display_menu = fields.Boolean()
    auto_lot = fields.Boolean(
        string="Get lots automatically",
        help="If checked the lot will be set automatically with the same "
        "removal startegy",
        compute="_compute_auto_lot",
        store=True,
        readonly=False,
    )
    create_lot = fields.Boolean(
        string="Allow create lot",
        help="Show lot name field",
        compute="_compute_create_lot",
    )
    display_assign_serial = fields.Boolean(compute="_compute_display_assign_serial")
    keep_result_package = fields.Boolean()
    total_product_uom_qty = fields.Float(
        string="Product Demand", digits="Product Unit of Measure", store=False
    )
    total_product_qty_done = fields.Float(
        string="Product Qty. Done", digits="Product Unit of Measure", store=False
    )

    @api.depends("res_id")
    def _compute_action_ids(self):
        actions = self.env["stock.barcodes.action"].search([])
        self.action_ids = actions

    @api.depends("option_group_id")
    def _compute_is_manual_qty(self):
        for rec in self:
            rec.is_manual_qty = rec.option_group_id.is_manual_qty
            rec.is_manual_confirm = rec.option_group_id.is_manual_confirm
            rec.auto_lot = rec.option_group_id.auto_lot

    @api.depends("option_group_id")
    def _compute_auto_lot(self):
        for rec in self:
            rec.auto_lot = rec.option_group_id.auto_lot

    @api.depends("option_group_id")
    def _compute_create_lot(self):
        for rec in self:
            rec.create_lot = rec.option_group_id.create_lot

    @api.depends("product_id")
    def _compute_display_assign_serial(self):
        for rec in self:
            rec.display_assign_serial = rec.product_id.tracking == "serial"

    @api.depends("lot_id")
    def _compute_lot_name(self):
        for rec in self:
            rec.lot_name = rec.lot_id.name

    @api.onchange("packaging_qty")
    def onchange_packaging_qty(self):
        if self.packaging_id:
            self.product_qty = self.packaging_qty * self.packaging_id.qty

    @api.onchange(
        "product_id",
        "lot_id",
        "package_id",
        "result_package_id",
        "packaging_qty",
        "product_qty",
    )
    def onchange_visible_force_done(self):
        self.visible_force_done = False

    def _set_messagge_info(self, message_type, message):
        """
        Set message type and message description.
        For manual entry mode barcode is not set so is not displayed
        """
        self.message_type = message_type
        # TODO: Uncomment this line when the tests of all modules have been adapted
        # if self.barcode and self.message_type in ["more_match", "not_found"]:
        if self.barcode:
            self.message = _(
                "%(barcode)s (%(message)s)", barcode=self.barcode, message=message
            )
        else:
            self.message = "%s" % message

    def process_barcode_location_id(self):
        location = self.env["stock.location"].search(self._barcode_domain(self.barcode))
        if location:
            self.location_id = location
            return True
        return False

    def process_barcode_location_dest_id(self):
        location = self.env["stock.location"].search(self._barcode_domain(self.barcode))
        if location:
            self.location_dest_id = location
            return True
        return False

    def process_barcode_product_id(self):
        domain = self._barcode_domain(self.barcode)
        product = self.env["product.product"].search(domain)
        if product:
            if len(product) > 1:
                self._set_messagge_info("more_match", _("More than one product found"))
                return False
            elif product.type not in self._allowed_product_types:
                self._set_messagge_info(
                    "not_found", _("The product type is not allowed")
                )
                return False
            self.action_product_scaned_post(product)
            if (
                self.option_group_id.fill_fields_from_lot
                and self.location_id
                and self.product_id
            ):
                quant_domain = [
                    ("location_id", "=", self.location_id.id),
                    ("product_id", "=", product.id),
                ]
                if self.lot_id:
                    quant_domain.append(("lot_id", "=", self.lot_id.id))
                if self.package_id:
                    quant_domain.append(("package_id", "=", self.package_id.id))
                if self.owner_id:
                    quant_domain.append(("owner_id", "=", self.owner_id.id))
                quants = self.env["stock.quant"].search(quant_domain)
                if quants:
                    self.set_info_from_quants(quants)
            return True
        return False

    def process_barcode_lot_id(self):
        if self.env.user.has_group("stock.group_production_lot"):
            lot_domain = [("name", "=", self.barcode)]
            if self.product_id:
                lot_domain.append(("product_id", "=", self.product_id.id))
            lot = self.env["stock.lot"].search(lot_domain)
            if len(lot) == 1:
                if self.option_group_id.fill_fields_from_lot:
                    quant_domain = [
                        ("lot_id.name", "=", self.barcode),
                        ("product_id", "=", lot.product_id.id),
                        ("quantity", ">", 0.0),
                    ]
                    if self.location_id:
                        quant_domain.append(("location_id", "=", self.location_id.id))
                    else:
                        quant_domain.append(("location_id.usage", "=", "internal"))
                    if self.owner_id:
                        quant_domain.append(("owner_id", "=", self.owner_id.id))
                    quants = self.env["stock.quant"].search(quant_domain)
                    if (
                        not self._name == "wiz.stock.barcodes.read.inventory"
                        and not quants
                        and not self.option_group_id.allow_negative_quant
                    ):
                        self._set_messagge_info(
                            "more_match",
                            _("No stock available for this lot with screen values"),
                        )
                        self.lot_id = False
                        self.lot_name = False
                        return False
                    if quants:
                        self.set_info_from_quants(quants)
                    else:
                        self.product_id = lot.product_id
                        self.action_lot_scaned_post(lot)
                    return True
                else:
                    self.product_id = lot.product_id
                    self.action_lot_scaned_post(lot)
                return True
            elif lot:
                self._set_messagge_info(
                    "more_match", _("More than one lot found\nScan product before")
                )
            elif (
                self.product_id
                and self.product_id.tracking != "none"
                and self.option_group_id.create_lot
            ):
                self.lot_name = self.barcode
                self.action_lot_scaned_post(self.lot_name)
                return True
        return False

    def process_barcode_package_id(self):
        if not self.env.user.has_group("stock.group_tracking_lot"):
            return False
        quant_domain = [
            ("package_id.name", "=", self.barcode),
            ("quantity", ">", 0.0),
        ]
        if self.option_group_id.get_option_value("location_id", "forced"):
            quant_domain.append(("location_id", "=", self.location_id.id))
        if self.owner_id:
            quant_domain.append(("owner_id", "=", self.owner_id.id))
        quants = self.env["stock.quant"].search(quant_domain)
        internal_quants = quants.filtered(lambda q: q.location_id.usage == "internal")
        if internal_quants:
            quants = internal_quants
        elif quants:
            self = self.with_context(ignore_quant_location=True)
            # self._set_messagge_info("more_match", _("Package located external location"))
        else:
            # self._set_messagge_info("more_match", _("Package not fount or empty"))
            return False
        self.set_info_from_quants(quants)
        return True

    def process_barcode_result_package_id(self):
        if not self.env.user.has_group("stock.group_tracking_lot"):
            return False
        domain = [("name", "=", self.barcode)]
        package = self.env["stock.quant.package"].search(domain)
        if package:
            self.result_package_id = package[:1]
            return True
        return False

    def set_info_from_quants(self, quants):
        """
        Fill wizard fields from stock quants
        """
        if self.env.context.get("skip_set_info_from_quants"):
            return
        ignore_quant_location = self.env.context.get(
            "ignore_quant_location", self.option_group_id.ignore_quant_location
        )
        if len(quants) == 1:
            # All ok
            self.action_product_scaned_post(quants.product_id)
            self.package_id = quants.package_id
            self.result_package_id = quants.package_id
            if quants.lot_id:
                self.action_lot_scaned_post(quants.lot_id)
            if quants.owner_id:
                self.owner_id = quants.owner_id
            # Review conditions
            if (
                not ignore_quant_location
                and not self.option_group_id.get_option_value("location_id", "forced")
                and self.option_group_id.code != "IN"
            ):
                self.location_id = quants.location_id
            if self.option_group_id.code != "OUT" and not self.env.context.get(
                "skip_update_quantity_from_lot", False
            ):
                self.product_qty = quants.quantity
        elif len(quants) > 1:
            # More than one record found with same barcode.
            # Could be half lot in two distinct locations.
            # Empty location field to force a location barcode scan
            products = quants.mapped("product_id")
            if len(products) == 1:
                self.action_product_scaned_post(products[0])
            package = quants[0].package_id
            if not quants.filtered(lambda q: q.package_id != package):
                self.package_id = package
            lots = quants.mapped("lot_id")
            if len(lots) == 1:
                self.action_lot_scaned_post(lots[0])
            owner = quants[0].owner_id
            if not quants.filtered(lambda q: q.owner_id != owner):
                self.owner_id = owner
            if not ignore_quant_location:
                locations = quants.mapped("location_id")
                if len(locations) == 1:
                    if not self.location_id and self.option_group_id.code != "IN":
                        self.location_id = locations

    def process_barcode_packaging_id(self):
        domain = self._barcode_domain(self.barcode)
        if self.env.user.has_group("product.group_stock_packaging"):
            domain.append(("product_id", "!=", False))
            packaging = self.env["product.packaging"].search(domain)
            if packaging:
                if len(packaging) > 1:
                    self._set_messagge_info(
                        "more_match", _("More than one package found")
                    )
                    self.packaging_id = False
                    return False
                self.action_packaging_scaned_post(packaging)
                return True
        return False

    def process_barcode(self, barcode):
        self._set_messagge_info("success", _("OK"))
        options = self.option_group_id.option_ids
        barcode_found = False
        options_to_scan = options.filtered("to_scan")
        options_required = options.filtered("required")
        options_to_scan = options_to_scan.filtered(lambda op: op.step == self.step)
        for option in options_to_scan:
            if (
                self.option_group_id.ignore_filled_fields
                and option in options_required
                and getattr(self, option.field_name, False)
            ):
                continue
            option_func = getattr(self, "process_barcode_%s" % option.field_name, False)
            if option_func:
                res = option_func()
                if res:
                    barcode_found = True
                    self.play_sounds(barcode_found)
                    break
                elif self.message_type != "success":
                    self.play_sounds(False)
                    return False
        if not barcode_found:
            self.play_sounds(barcode_found)
            if self.option_group_id.ignore_filled_fields:
                self._set_messagge_info(
                    "info", _("Barcode not found or field already filled")
                )
            else:
                self._set_messagge_info(
                    "not_found", _("Barcode not found with this screen values")
                )
            self.display_notification(
                self.barcode,
                message_type="danger",
                title=_("Barcode not found"),
                sticky=False,
            )
            return False
        if not self.check_option_required():
            return False
        if self.is_manual_confirm or self.manual_entry:
            self._set_messagge_info("info", _("Review and confirm"))
            return False
        return self.action_confirm()

    def check_option_required(self):
        options = self.option_group_id.option_ids
        options_required = options.filtered("required")
        for option in options_required:
            if not getattr(self, option.field_name, False):
                if self.is_manual_qty and option.field_name in [
                    "product_qty",
                    "packaging_qty",
                ]:
                    self._set_focus_on_qty_input("product_qty")
                if option.field_name == "lot_id" and (
                    self.product_id.tracking == "none"
                    or self.auto_lot
                    or (self.lot_name and self.create_lot)
                ):
                    continue
                if self._option_required_hook(option):
                    continue
                self.display_notification(
                    _("{name} is required").format(name=option.name),
                    message_type="danger",
                    title=_("Empty field"),
                    sticky=False,
                )
                self.action_show_step()
                return False
        return True

    def _option_required_hook(self, option_required):
        """Hook to evaluate is an option is required"""
        return False

    def _scanned_location(self, barcode):
        location = self.env["stock.location"].search(self._barcode_domain(barcode))
        if location:
            self.location_id = location
            self._set_messagge_info("info", _("Waiting product"))
            return True
        else:
            return False

    def _barcode_domain(self, barcode):
        field_name = self.env.context.get("barcode_domain_field", "barcode")
        return [(field_name, "=", barcode)]

    def _clean_barcode_scanned(self, barcode):
        return barcode.rstrip()

    def on_barcode_scanned(self, barcode):
        self.barcode = self._clean_barcode_scanned(barcode)

    def dummy_on_barcode_scanned(self):
        """To avoid execute operations in onchange environment"""
        self.process_barcode(self.barcode)

    def check_location_contidion(self):
        if not self.location_id:
            self._set_messagge_info("info", _("Waiting location"))
            # Remove product when no location has been scanned
            self.product_id = False
            return False
        return True

    def check_lot_contidion(self):
        if self.product_id.tracking != "none" and not self.lot_id and not self.lot_name:
            self._set_messagge_info("info", _("Waiting lot"))
            return False
        return True

    def check_done_conditions(self):
        result_ok = self.check_location_contidion()
        if not result_ok:
            return False
        if not self.product_id:
            self._set_messagge_info("info", _("Waiting product"))
            return False
        result_ok = self.check_lot_contidion()
        if not result_ok:
            return False
        if (
            not self.product_qty
            and not self._name == "wiz.stock.barcodes.read.inventory"
        ):
            self._set_messagge_info("info", _("Waiting quantities"))
            return False
        if (
            self.option_group_id.barcode_guided_mode == "guided"
            and not self._check_guided_values()
        ):
            return False
        if self.manual_entry:
            self._set_messagge_info("success", _("Manual entry OK"))
        return True

    def _check_guided_values(self):
        if (
            self.product_id != self.guided_product_id
            and self.option_group_id.get_option_value("product_id", "forced")
        ):
            self._set_messagge_info("more_match", _("Wrong product"))
            self.product_qty = 0.0
            return False
        if (
            self.guided_product_id.tracking != "none"
            and self.lot_id != self.guided_lot_id
            and self.option_group_id.get_option_value("lot_id", "forced")
        ):
            self._set_messagge_info("more_match", _("Wrong lot"))
            return False
        if (
            self.location_id != self.guided_location_id
            and self.option_group_id.get_option_value("location_id", "forced")
        ):
            self._set_messagge_info("more_match", _("Wrong location"))
            return False
        if (
            self.location_dest_id != self.guided_location_dest_id
            and self.option_group_id.get_option_value("location_dest_id", "forced")
        ):
            self._set_messagge_info("more_match", _("Wrong location dest"))
            return False
        return True

    def action_done(self):
        if not self.manual_entry and not self.product_qty and not self.is_manual_qty:
            self.product_qty = 1.0
        limit_product_qty = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock_barcodes.limit_product_qty", "999999")
        )
        if self.product_qty > limit_product_qty:
            # HACK: Some times users scan a barcode into input element.
            # At this time, to prevent this we check that the quantity be realistic.
            self._set_messagge_info("more_match", _("The quantity is huge"))
            return False
        if not self.check_done_conditions():
            return False
        self.process_lot_before_done()
        return True

    def action_cancel(self):
        return True

    def action_product_scaned_post(self, product):
        self.package_id = False
        if self.product_id != product and self.lot_id.product_id != product:
            self.lot_id = False
        self.product_id = product
        self.product_uom_id = self.product_id.uom_id
        self.set_product_qty()

    def action_packaging_scaned_post(self, packaging):
        self.packaging_id = packaging
        if (
            self.product_id != packaging.product_id
            and self.lot_id.product_id != packaging.product_id
        ):
            self.lot_id = False
        self.product_id = packaging.product_id
        self.set_product_qty()

    def action_lot_scaned_post(self, lot):
        if isinstance(lot, str):
            self.lot_name = lot
        else:
            self.lot_id = lot
        self.set_product_qty()

    def set_product_qty(self):
        if (
            self.manual_entry
            or self.is_manual_qty
            or self.option_group_id.get_option_value("product_qty", "filled_default")
        ):
            return
        elif self.packaging_id:
            self.packaging_qty = 1.0
            self.product_qty = self.packaging_id.qty * self.packaging_qty
        else:
            self.packaging_qty = 0.0
            self.product_qty = 1.0

    def action_clean_lot(self):
        self.lot_id = False
        self.lot_name = False
        self.action_show_step()

    def action_clean_product(self):
        self.product_id = False
        self.action_show_step()

    def action_clean_package(self):
        self.package_id = False
        self.result_package_id = False
        self.action_show_step()

    def action_create_package(self):
        self.result_package_id = self.env["stock.quant.package"].create({})

    def action_clean_values(self):
        options = self.option_group_id.option_ids
        options_to_clean = options.filtered(
            lambda op: op.clean_after_done and op.field_name in self
        )
        for option in options_to_clean:
            if option.field_name == "result_package_id" and self.keep_result_package:
                continue
            if option.field_name:
                setattr(self, option.field_name, False)
        self.action_show_step()
        self.product_qty = 0.0
        self.packaging_qty = 0.0
        self.lot_name = False

    def action_manual_entry(self):
        return True

    # TODO: To remove when stock_move_location uses action_clean_values
    def reset_qty(self):
        self.product_qty = 0
        self.packaging_qty = 0

    def open_actions(self):
        self.display_menu = True

    def action_back(self):
        self.display_menu = False

    def open_records(self):
        action = self.action_ids
        return action

    def get_option_value(self, field_name, attribute):
        option = self.option_group_id.option_ids.filtered(
            lambda op: op.field_name == field_name
        )[:1]
        return option[attribute]

    def action_force_done(self):
        res = self.with_context(force_create_move=True).action_confirm()
        self.visible_force_done = False
        return res

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wiz in wizards:
            wiz.action_show_step()
        return wizards

    def action_manual_quantity(self):
        action = self.get_formview_action()
        form_view = self.env.ref(
            "stock_barcodes.view_stock_barcodes_read_form_manual_qty"
        )
        action["views"] = [(form_view.id, "form")]
        action["res_id"] = self.ids[0]
        return action

    def action_reopen_wizard(self):
        return self.get_formview_action()

    @api.onchange("step")
    def action_show_step(self):
        options_required = self.option_group_id.option_ids.filtered("required")
        self.step = 0
        for option in options_required:
            if not getattr(self, option.field_name, False):
                if option.field_name == "lot_id" and self.product_id.tracking == "none":
                    continue
                self.step = option.step
                break
        if not self.step:
            self.step = options_required[:1].step

        options = self.option_group_id.option_ids.filtered(
            lambda op: op.step == self.step and op.to_scan
        )
        self._set_messagge_info(
            "info", _("Scan {}").format(", ".join(options.mapped("name")))
        )

    @api.onchange("package_id")
    def onchange_package_id(self):
        if self.manual_entry:
            self.barcode = self.package_id.name
            self.process_barcode_package_id()

    def action_confirm(self):
        if not self.check_option_required():
            self.play_sounds(False)
            return False
        record = self.browse(self.ids)
        record.write(self._convert_to_write(self._cache))
        self = record
        res = self.action_done()
        self.invalidate_recordset()
        self.play_sounds(res)
        self._set_focus_on_qty_input()
        return res

    def process_lot_before_done(self):
        if (
            not self.lot_id
            and self.lot_name
            and self.product_id
            and self.product_id.tracking != "none"
            and self.option_group_id.create_lot
        ):
            self.lot_id = self._create_new_lot()
        return True

    def play_sounds(self, res):
        if res:
            self.env["bus.bus"]._sendone(
                "stock_barcodes_scan",
                "stock_barcodes_sound",
                {"sound": "ok", "res_model": self._name, "res_id": self.ids[0]},
            )
        else:
            self.env["bus.bus"]._sendone(
                "stock_barcodes_scan",
                "stock_barcodes_sound",
                {"sound": "ko", "res_model": self._name, "res_id": self.ids[0]},
            )

    def _set_focus_on_qty_input(self, field_name=None):
        if field_name is None:
            field_name = "product_qty"
        if field_name == "product_qty" and self.packaging_id:
            field_name = "packaging_qty"
        self.env["bus.bus"]._sendone(
            "stock_barcodes_scan",
            "stock_barcodes_focus",
            {
                "action": "focus",
                "field_name": field_name,
                "res_model": self._name,
                "res_id": self.ids[0],
            },
        )

    @api.onchange("product_id")
    def onchange_product_id(self):
        self.product_uom_id = self.product_id.uom_id

    @api.onchange("manual_entry")
    def onchange_manual_entry(self):
        if self.manual_entry and self.option_group_id.manual_entry_field_focus:
            self._set_focus_on_qty_input(self.option_group_id.manual_entry_field_focus)

    def _prepare_lot_vals(self):
        return {
            "name": self.lot_name,
            "product_id": self.product_id.id,
            "company_id": self.env.company.id,
        }

    def _create_new_lot(self):
        StockProductionLot = self.env["stock.lot"]
        lot_domain = [
            ("name", "=", self.lot_name),
            ("product_id", "=", self.product_id.id),
        ]
        new_lot = StockProductionLot.search(lot_domain)
        if not new_lot:
            new_lot = StockProductionLot.create(self._prepare_lot_vals())
        return new_lot

    def action_clean_message(self):
        self.message = False
        self.check_option_required()

    def action_keep_result_package(self):
        self.keep_result_package = not self.keep_result_package

    def display_notification(
        self, message, message_type="warning", title=False, sticky=True
    ):
        """Send notifications to web client
        message_type:
         [options.type='warning'] 'info', 'success', 'warning', 'danger' or ''
         sticky: Permanent notification until user removes it
        """
        if self.option_group_id.display_notification and not self.env.context.get(
            "skip_display_notification", False
        ):
            message = {
                "message": message,
                "type": message_type,
                "sticky": sticky,
                "res_model": self._name,
                "res_id": self.ids[0],
            }
            if title:
                message["title"] = title
            self.env["bus.bus"]._sendone(
                "stock_barcodes-{}".format(self.ids[0]),
                "stock_barcodes_notify-{}".format(self.ids[0]),
                message,
            )
