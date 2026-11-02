# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models


class Od19BillingRequest(models.Model):
    _name = "od19.billing.request"
    _description = "OD19 Billing Request"
    _inherit = ["mail.thread", "mail.activity.mixin", "od19.document.pull.mixin"]
    _order = "date_request desc, id desc"

    name = fields.Char(
        string="Number / เลขที่คำขอ", default="/", copy=False, readonly=True
    )
    direction = fields.Selection(
        [("ar", "AR - ลูกหนี้ / Customer"), ("ap", "AP - เจ้าหนี้ / Vendor")],
        string="Direction / ทิศทาง",
        required=True,
        default="ar",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("invoiced", "Invoiced"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status / สถานะ",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    date_request = fields.Date(
        string="Request Date / วันที่แจ้ง",
        default=fields.Date.context_today,
        required=True,
    )
    note = fields.Text(string="Note / หมายเหตุ")

    # --- ผู้แจ้ง ---
    requested_by_id = fields.Many2one(
        "res.users",
        string="Requested By / ผู้แจ้ง",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    requested_employee_id = fields.Many2one(
        "hr.employee",
        string="Requested Employee / พนักงานผู้แจ้ง",
        compute="_compute_requester_info",
        store=True,
        readonly=False,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department / แผนก",
        compute="_compute_requester_info",
        store=True,
        readonly=False,
        index=True,
    )

    # --- ต้นทาง/ปลายทาง ---
    origin_ref = fields.Reference(
        selection="_selection_origin_ref",
        string="Origin / เอกสารต้นทาง",
        tracking=True,
    )
    origin_model = fields.Char(
        string="Origin Model",
        compute="_compute_origin_info",
        store=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner / คู่ค้า",
        compute="_compute_origin_info",
        store=True,
        readonly=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )
    move_type = fields.Selection(
        [("out_invoice", "Customer Invoice"), ("in_invoice", "Vendor Bill")],
        string="Target Document Type",
        compute="_compute_move_type",
    )
    target_move_id = fields.Many2one(
        "account.move",
        string="Target Invoice/Bill / เอกสารปลายทาง",
        readonly=True,
        copy=False,
    )

    # --- นโยบาย AR ---
    ar_billing_mode = fields.Selection(
        [("direct", "Direct / ออกบิลเลย"), ("two_step", "Two Step / วางบิลก่อน")],
        string="AR Billing Mode / โหมดวางบิล AR",
        compute="_compute_ar_billing_mode",
        store=True,
        readonly=False,
    )

    # --- ต้นฉบับจริง (AP) ---
    original_received = fields.Boolean(
        string="Original Document Received / รับต้นฉบับจริงแล้ว", tracking=True
    )
    original_received_date = fields.Date(string="Original Received Date / วันที่รับต้นฉบับ")
    original_received_by_id = fields.Many2one(
        "res.users", string="Original Received By / ผู้รับต้นฉบับ"
    )

    reject_reason = fields.Text(string="Reject Reason / เหตุผลที่ตีกลับ")
    line_ids = fields.One2many(
        "od19.billing.request.line", "request_id", string="Lines / รายการ"
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.model
    def _selection_origin_ref(self):
        return [
            ("stock.picking", _("Transfer / ใบรับ-ส่งสินค้า")),
            ("sale.order", _("Sale Order / ใบสั่งขาย")),
            ("purchase.order", _("Purchase Order / ใบสั่งซื้อ")),
        ]

    @api.model
    def _od19_employee_for_user(self, user):
        if not user:
            return self.env["hr.employee"]
        return user.sudo().employee_id

    @api.depends("requested_by_id")
    def _compute_requester_info(self):
        for request in self:
            employee = request._od19_employee_for_user(request.requested_by_id)
            request.requested_employee_id = employee
            request.department_id = employee.department_id if employee else False

    @api.depends("origin_ref")
    def _compute_origin_info(self):
        for request in self:
            origin = request.origin_ref
            request.origin_model = origin._name if origin else False
            if origin and not request.partner_id:
                request.partner_id = getattr(origin, "partner_id", False)

    @api.depends("direction")
    def _compute_move_type(self):
        for request in self:
            request.move_type = (
                "out_invoice" if request.direction == "ar" else "in_invoice"
            )

    @api.depends("direction", "partner_id", "origin_ref", "company_id")
    def _compute_ar_billing_mode(self):
        for request in self:
            mode = False
            origin = request.origin_ref
            if origin and origin._name == "sale.order":
                mode = origin.od19_ar_billing_mode
            if (not mode or mode == "default") and request.partner_id:
                mode = request.partner_id.od19_ar_billing_mode
            if not mode or mode == "default":
                mode = request.company_id.od19_ar_billing_mode_default or "direct"
            request.ar_billing_mode = mode

    # ------------------------------------------------------------------
    # Sequence
    # ------------------------------------------------------------------
    @api.model
    def _od19_get_billing_request_sequence(self, direction):
        """Return (creating on demand) the sequence for the given direction."""
        sequence_model = self.env["ir.sequence"].sudo()
        code = "od19.billing.request.%s" % (direction or "ar")
        prefix = "BRI/%s/" % (direction or "ar").upper()
        sequence = sequence_model.search([("code", "=", code)], limit=1)
        if not sequence:
            sequence = sequence_model.create(
                {
                    "name": "Billing Request %s" % (direction or "ar").upper(),
                    "code": code,
                    "prefix": prefix,
                    "padding": 5,
                    "company_id": False,
                }
            )
        return sequence

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                direction = vals.get("direction") or "ar"
                vals["name"] = self._od19_get_billing_request_sequence(
                    direction
                ).next_by_id()
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Document pull contract (od19.document.pull.mixin)
    # ------------------------------------------------------------------
    def _od19_pull_editable_states(self):
        return ("draft",)

    def _od19_pull_source_specs(self):
        self.ensure_one()
        partner_domain = (
            [("partner_id", "=", self.partner_id.id)] if self.partner_id else []
        )
        if self.direction == "ap":
            return [
                {
                    "model": "purchase.order",
                    "label": _("Purchase Order / ใบสั่งซื้อ"),
                    "domain": partner_domain + [("state", "in", ("purchase", "done"))],
                },
                {
                    "model": "stock.picking",
                    "label": _("Receipt / ใบรับของ"),
                    "domain": partner_domain
                    + [("picking_type_code", "=", "incoming"), ("state", "=", "done")],
                },
            ]
        return [
            {
                "model": "sale.order",
                "label": _("Sale Order / ใบสั่งขาย"),
                "domain": partner_domain + [("state", "=", "sale")],
            },
            {
                "model": "stock.picking",
                "label": _("Delivery / ใบส่งของ"),
                "domain": partner_domain
                + [("picking_type_code", "=", "outgoing"), ("state", "=", "done")],
            },
        ]

    def _od19_pull_candidate_lines(self, source):
        self.ensure_one()
        if source._name in ("sale.order", "purchase.order"):
            return source.order_line.filtered(
                lambda line: line.product_id and line.qty_to_invoice > 0
            )
        if source._name == "stock.picking":
            return source.move_ids.filtered(
                lambda move: move.product_id and move.quantity > 0
            )
        return self.env["od19.billing.request.line"].browse()

    def _od19_pull_line_info(self, source, line):
        self.ensure_one()
        if source._name in ("sale.order", "purchase.order"):
            return {
                "res_model": source._name,
                "res_id": line.id,
                "source_name": source.display_name,
                "product_id": line.product_id.id,
                "name": line.name,
                "qty_to_pull": line.qty_to_invoice,
                "price_unit": line.price_unit,
                "product_uom_id": line.product_uom_id.id,
            }
        sale_line = line.sale_line_id
        price = sale_line.price_unit if sale_line else (line.price_unit or 0.0)
        return {
            "res_model": source._name,
            "res_id": line.id,
            "source_name": source.display_name,
            "product_id": line.product_id.id,
            "name": line.description_picking or line.product_id.display_name,
            "qty_to_pull": line.quantity,
            "price_unit": price,
            "product_uom_id": line.product_uom.id,
        }

    def _od19_pull_apply(self, source, lines):
        self.ensure_one()
        count = 0
        if not self.origin_ref:
            self.origin_ref = source
        for src_line in lines:
            info = self._od19_pull_line_info(source, src_line)
            vals = {
                "request_id": self.id,
                "product_id": info["product_id"],
                "name": info["name"],
                "quantity": info["qty_to_pull"],
                "price_unit": info["price_unit"],
                "product_uom_id": info["product_uom_id"],
                "origin_line_model": source._name,
                "origin_line_id": src_line.id,
            }
            if source._name == "sale.order":
                vals["sale_line_id"] = src_line.id
            elif source._name == "purchase.order":
                vals["purchase_line_id"] = src_line.id
            else:  # stock.picking
                vals["stock_move_id"] = src_line.id
                if src_line.sale_line_id:
                    vals["sale_line_id"] = src_line.sale_line_id.id
                if src_line.purchase_line_id:
                    vals["purchase_line_id"] = src_line.purchase_line_id.id
            self.env["od19.billing.request.line"].create(vals)
            count += 1
        return count

    def _od19_pull_origin_line_ids(self, source):
        self.ensure_one()
        if source._name in ("sale.order", "purchase.order"):
            return source.order_line.ids
        return source.move_ids.ids

    def _od19_pull_bound_lines(self, source):
        self.ensure_one()
        ids = self._od19_pull_origin_line_ids(source)
        return self.line_ids.filtered(
            lambda line: line.origin_line_model == source._name
            and line.origin_line_id in ids
        )

    def _od19_pull_remove(self, source):
        self.ensure_one()
        lines = self._od19_pull_bound_lines(source)
        count = len(lines)
        lines.unlink()
        return count

    def _od19_pull_bound_sources(self):
        self.ensure_one()
        result = []
        line_models = {
            "sale.order": "sale.order.line",
            "purchase.order": "purchase.order.line",
            "stock.picking": "stock.move",
        }
        for model, line_model in line_models.items():
            model_lines = self.line_ids.filtered(
                lambda line: line.origin_line_model == model
            )
            if not model_lines:
                continue
            records = self.env[line_model].browse(
                model_lines.mapped("origin_line_id")
            )
            if model in ("sale.order", "purchase.order"):
                for order in records.mapped("order_id"):
                    result.append((order, len(self._od19_pull_bound_lines(order))))
            else:
                for picking in records.mapped("picking_id"):
                    result.append((picking, len(self._od19_pull_bound_lines(picking))))
        return result

    def _od19_pull_preview_lines(self, source):
        self.ensure_one()
        return [
            {
                "name": line.name,
                "product_id": line.product_id.id,
                "quantity": line.quantity,
            }
            for line in self._od19_pull_bound_lines(source)
        ]
