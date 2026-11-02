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
