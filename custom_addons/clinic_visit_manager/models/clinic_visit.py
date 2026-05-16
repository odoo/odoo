# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import str2bool

GROUP_RECEPTIONIST = "clinic_visit_manager.group_clinic_receptionist"
GROUP_DOCTOR = "clinic_visit_manager.group_clinic_doctor"
GROUP_MANAGER = "clinic_visit_manager.group_clinic_manager"
WORKFLOW_CONTEXT_KEY = "clinic_visit_workflow_action"

WORKFLOW_FIELDS = frozenset(
    {
        "state",
        "queued_at",
        "consultation_started_at",
        "completed_at",
        "token_number",
    }
)
RECEPTIONIST_WRITE_FIELDS = frozenset(
    {
        "patient_name",
        "patient_id",
        "doctor_name",
        "visit_date",
        "fee",
        "symptoms",
        "temperature_celsius",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "pulse_rate",
        "respiratory_rate",
        "oxygen_saturation",
        "weight_kg",
        "height_cm",
    }
)
DOCTOR_WRITE_FIELDS = frozenset(
    {
        "symptoms",
        "temperature_celsius",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "pulse_rate",
        "respiratory_rate",
        "oxygen_saturation",
        "weight_kg",
        "height_cm",
        "notes",
    }
)

VISIT_STATES = [
    ("draft", "Draft"),
    ("waiting", "Waiting"),
    ("in_consultation", "In Consultation"),
    ("done", "Done"),
    ("cancelled", "Cancelled"),
]


class ClinicVisit(models.Model):
    _name = "clinic.visit"
    _description = "Clinic Visit"
    _order = "visit_date desc, id desc"

    name = fields.Char(
        string="Visit Reference",
        required=True,
        default="New Visit",
    )

    patient_name = fields.Char(
        string="Patient Name",
        required=True,
    )

    patient_id = fields.Many2one(
        "clinic.patient",
        string="Patient Card",
        ondelete="restrict",
    )

    token_number = fields.Char(
        string="Token",
        readonly=True,
        copy=False,
        index=True,
    )

    doctor_name = fields.Char(
        string="Doctor Name",
    )

    visit_date = fields.Datetime(
        string="Visit Date",
        default=fields.Datetime.now,
    )

    queued_at = fields.Datetime(
        string="Queued At",
        readonly=True,
        copy=False,
    )

    consultation_started_at = fields.Datetime(
        string="Consultation Started At",
        readonly=True,
        copy=False,
    )

    completed_at = fields.Datetime(
        string="Completed At",
        readonly=True,
        copy=False,
    )

    symptoms = fields.Text(
        string="Symptoms",
    )

    temperature_celsius = fields.Float(
        string="Temperature (C)",
        digits=(4, 1),
    )

    blood_pressure_systolic = fields.Integer(
        string="Systolic BP",
    )

    blood_pressure_diastolic = fields.Integer(
        string="Diastolic BP",
    )

    pulse_rate = fields.Integer(
        string="Pulse Rate",
    )

    respiratory_rate = fields.Integer(
        string="Respiratory Rate",
    )

    oxygen_saturation = fields.Float(
        string="Oxygen Saturation (%)",
        digits=(5, 2),
    )

    weight_kg = fields.Float(
        string="Weight (kg)",
        digits=(6, 2),
    )

    height_cm = fields.Float(
        string="Height (cm)",
        digits=(6, 2),
    )

    bmi = fields.Float(
        string="BMI",
        compute="_compute_bmi",
        digits=(5, 2),
        store=True,
    )

    fee = fields.Float(
        string="Consultation Fee",
    )

    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        readonly=True,
        copy=False,
        ondelete="set null",
        domain=[("move_type", "=", "out_invoice")],
    )

    invoice_payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Payment Status",
        readonly=True,
    )

    state = fields.Selection(
        VISIT_STATES,
        string="Status",
        default="draft",
        required=True,
    )

    notes = fields.Text(
        string="Doctor Notes",
    )

    queue_wait_minutes = fields.Integer(
        string="Wait Minutes",
        compute="_compute_timing_minutes",
    )

    consultation_minutes = fields.Integer(
        string="Consultation Minutes",
        compute="_compute_timing_minutes",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_visit_defaults(vals)
            self._check_visit_field_permissions(vals, creating=True)
            self._sync_patient_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if "state" in vals and not self.env.context.get(WORKFLOW_CONTEXT_KEY):
            self._check_workflow_groups((GROUP_MANAGER,))
        self._check_visit_field_permissions(vals)
        if "patient_name" in vals or "patient_id" in vals:
            self._sync_patient_values(vals)
        return super().write(vals)

    @api.depends("weight_kg", "height_cm")
    def _compute_bmi(self):
        for record in self:
            height_m = record.height_cm / 100
            record.bmi = (
                record.weight_kg / (height_m * height_m)
                if record.weight_kg and height_m
                else 0.0
            )

    @api.depends("queued_at", "consultation_started_at", "completed_at")
    def _compute_timing_minutes(self):
        now = fields.Datetime.now()
        for record in self:
            queue_end = record.consultation_started_at or record.completed_at or now
            consultation_end = record.completed_at or now
            record.queue_wait_minutes = self._minutes_between(
                record.queued_at,
                queue_end,
            )
            record.consultation_minutes = self._minutes_between(
                record.consultation_started_at,
                consultation_end,
            )

    @staticmethod
    def _minutes_between(start, end):
        if not start or not end or end < start:
            return 0
        return int((end - start).total_seconds() // 60)

    def _apply_visit_defaults(self, vals):
        config = self.env["ir.config_parameter"].sudo()
        if not vals.get("doctor_name"):
            vals["doctor_name"] = config.get_param(
                "clinic_visit_manager.default_doctor_name",
                "",
            )
        if not vals.get("fee"):
            vals["fee"] = float(
                config.get_param(
                    "clinic_visit_manager.default_consultation_fee",
                    "0.0",
                )
            )

    def _should_auto_create_patient(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "clinic_visit_manager.auto_create_patient",
            "False",
        )
        return str2bool(value)

    def _sync_patient_values(self, vals):
        patient_id = vals.get("patient_id")
        patient_name = (vals.get("patient_name") or "").strip()

        if patient_id and not patient_name:
            patient = self.env["clinic.patient"].browse(patient_id)
            vals["patient_name"] = getattr(patient, "name", "")
            return

        if patient_name and not patient_id and self._should_auto_create_patient():
            vals["patient_id"] = self._get_or_create_patient(patient_name).id

    def _get_or_create_patient(self, patient_name):
        patient_name = patient_name.strip()
        patient = self.env["clinic.patient"].search(
            [("name", "=ilike", patient_name)],
            limit=1,
        )
        if patient:
            return patient
        return self.env["clinic.patient"].create({"name": patient_name})

    def _get_invoice_product(self):
        product_id = self.env["ir.config_parameter"].sudo().get_param(
            "clinic_visit_manager.invoice_product_id"
        )
        product = self.env["product.product"].browse(int(product_id or 0)).exists()
        if not product:
            raise UserError(
                _(
                    "Select an invoice product in Clinic Settings before creating invoices."
                )
            )
        return product

    def _get_or_create_invoice_partner(self):
        self.ensure_one()
        if self.patient_id and self.patient_id.partner_id:
            return self.patient_id.partner_id

        partner_vals = {
            "name": self.patient_name,
            "customer_rank": 1,
        }
        if self.patient_id:
            partner_vals.update(
                {
                    "phone": self.patient_id.phone,
                    "email": self.patient_id.email,
                }
            )

        partner = self.env["res.partner"].sudo().create(partner_vals)
        if self.patient_id:
            self.patient_id.sudo().partner_id = partner.id
        return partner

    def action_create_invoice(self):
        can_invoice = (
            self.env.user.has_group("account.group_account_invoice")
            or self.env.user.has_group(GROUP_RECEPTIONIST)
            or self.env.user.has_group(GROUP_MANAGER)
        )
        if not can_invoice:
            raise AccessError(_("You need Odoo Invoicing access to create invoices."))

        product = self._get_invoice_product()
        invoice_action = False
        for record in self:
            if record.invoice_id:
                raise UserError(_("This visit already has an invoice."))
            if record.state == "cancelled":
                raise UserError(_("Cancelled visits cannot be invoiced."))
            if not record.fee:
                raise UserError(_("Set a consultation fee before creating an invoice."))

            partner = record._get_or_create_invoice_partner()
            invoice = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "invoice_origin": record.token_number or record.name,
                    "invoice_date": fields.Date.context_today(record),
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "quantity": 1.0,
                                "price_unit": record.fee,
                            }
                        )
                    ],
                }
            )
            record.sudo().write({"invoice_id": invoice.id})
            invoice_action = record.action_view_invoice()
        return invoice_action

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice is linked to this visit."))
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice"
        )
        action.update(
            {
                "res_id": self.invoice_id.id,
                "views": [(False, "form")],
                "context": {"default_move_type": "out_invoice"},
            }
        )
        return action

    def _check_workflow_groups(self, group_xmlids):
        if self.env.su:
            return
        if any(self.env.user.has_group(group_xmlid) for group_xmlid in group_xmlids):
            return
        raise AccessError(
            _("You do not have permission to perform this clinic workflow action.")
        )

    def _check_visit_field_permissions(self, vals, creating=False):
        if self.env.su or self.env.user.has_group(GROUP_MANAGER):
            return

        fields_to_check = set(vals)
        if self.env.context.get(WORKFLOW_CONTEXT_KEY):
            fields_to_check -= WORKFLOW_FIELDS
        fields_to_check.discard("name")

        if not fields_to_check:
            return

        allowed_fields = set()
        if self.env.user.has_group(GROUP_RECEPTIONIST):
            allowed_fields |= RECEPTIONIST_WRITE_FIELDS
        if self.env.user.has_group(GROUP_DOCTOR) and not creating:
            allowed_fields |= DOCTOR_WRITE_FIELDS

        forbidden_fields = fields_to_check - allowed_fields
        if forbidden_fields:
            field_labels = [
                self._fields[field_name].string
                for field_name in sorted(forbidden_fields)
                if field_name in self._fields
            ]
            raise AccessError(
                _(
                    "Your clinic role does not allow editing these fields: %(fields)s"
                )
                % {"fields": ", ".join(field_labels or sorted(forbidden_fields))}
            )

    def action_confirm(self):
        self._check_workflow_groups((GROUP_RECEPTIONIST, GROUP_MANAGER))
        for record in self:
            if not record.patient_name:
                raise UserError("Patient name is required.")
            vals = {"state": "waiting"}
            if not record.queued_at:
                vals["queued_at"] = fields.Datetime.now()
            if not record.token_number:
                vals["token_number"] = self.env["ir.sequence"].next_by_code(
                    "clinic.visit.token"
                )
            record.with_context(**{WORKFLOW_CONTEXT_KEY: True}).write(vals)

    def action_start_consultation(self):
        self._check_workflow_groups((GROUP_DOCTOR, GROUP_MANAGER))
        for record in self:
            if record.state != "waiting":
                raise UserError("Only waiting visits can start consultation.")
            vals = {"state": "in_consultation"}
            if not record.consultation_started_at:
                vals["consultation_started_at"] = fields.Datetime.now()
            record.with_context(**{WORKFLOW_CONTEXT_KEY: True}).write(vals)

    def action_done(self):
        self._check_workflow_groups((GROUP_DOCTOR, GROUP_MANAGER))
        for record in self:
            if record.state not in ("waiting", "in_consultation"):
                raise UserError("Only active visits can be marked as done.")
            vals = {"state": "done"}
            if not record.completed_at:
                vals["completed_at"] = fields.Datetime.now()
            if record.state == "waiting" and not record.consultation_started_at:
                vals["consultation_started_at"] = vals["completed_at"]
            record.with_context(**{WORKFLOW_CONTEXT_KEY: True}).write(vals)

    def action_cancel(self):
        self._check_workflow_groups((GROUP_RECEPTIONIST, GROUP_MANAGER))
        for record in self:
            if record.state == "done":
                raise UserError("Done visits cannot be cancelled.")
            record.with_context(**{WORKFLOW_CONTEXT_KEY: True}).write(
                {"state": "cancelled"}
            )
