# See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StudentTransport(models.Model):
    _name = "student.transport"
    _description = "Transport Information"


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    @api.depends("vehi_participants_ids")
    def _compute_participants(self):
        """Method to get number participant."""
        for rec in self:
            rec.participant_count = len(
                rec.vehi_participants_ids.filtered(
                    lambda r: r.vehicle_id.id == rec.id and r.state != "over"
                )
            )

    participant_count = fields.Integer(
        compute="_compute_participants",
        string="Total Participants",
        readonly=True,
        help="Students registered in root",
    )
    vehi_participants_ids = fields.Many2many(
        "transport.participant",
        "vehicle_participant_student_rel",
        "vehicle_id",
        "student_id",
        "Vehicle Participants",
        help="Select vehicle participants",
    )

    def action_show_participant(self):
        """This opens the xml view specified in
        xml_id for the current vehicle"""
        self.ensure_one()
        xml_id = self.env.context.get("xml_id")
        if xml_id:
            res = self.env["ir.actions.act_window"]._for_xml_id(
                "school_transport.%s" % xml_id
            )
            res.update(
                context=dict(
                    self.env.context,
                    default_vehicle_id=self.id,
                    group_by=False,
                ),
                domain=[("vehicle_id", "=", self.id)],
            )
            return res
        return False

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        if self._context.get("name"):
            student_obj = self.env["student.transport"]
            student_rec = student_obj.browse(self._context.get("name"))
            args += [("id", "in", student_rec.sudo().trans_vehicle_ids.ids)]
        return super(FleetVehicle, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class ResPartner(models.Model):
    _inherit = "res.partner"

    licence_no = fields.Char(string="License No", help="Enter License No.")

    @api.constrains("licence_no")
    def check_licence_number(self):
        """Constraint for unique licence number"""
        driver_rec = self.search(
            [("licence_no", "=", self.licence_no), ("id", "not in", self.ids)]
        )
        if driver_rec:
            raise ValidationError(
                _(
                    """ The licence number you have entered already exist.
                Please enter different licence number!"""
                )
            )


class TransportParticipant(models.Model):
    """for participants."""

    _name = "transport.participant"
    _rec_name = "stu_pid_id"
    _description = "Transport Participant Information"

    name = fields.Many2one(
        "student.student",
        "Participant Name",
        readonly=True,
        required=True,
        help="Select student as transport participant",
    )
    amount = fields.Float(readonly=True, help="Enter amount")
    transport_id = fields.Many2one(
        "student.transport",
        "Transport Root",
        readonly=True,
        required=True,
        help="Select student transport",
    )
    stu_pid_id = fields.Char(
        "Personal Identification Number",
        required=True,
        help="Enter student PI No.",
    )
    tr_reg_date = fields.Date(
        "Transportation Registration Date", help="Start date of registration"
    )
    tr_end_date = fields.Date("Registration End Date", help="End date of registration")
    months = fields.Integer("Registration For Months", help="Registration for months")
    vehicle_id = fields.Many2one(
        "fleet.vehicle", "Vehicle No", help="Enter vehicle no."
    )
    state = fields.Selection(
        [("running", "Running"), ("over", "Over")],
        readonly=True,
        help="State of the transport participant",
    )
    active = fields.Boolean(
        default=True,
        help="Marked transport participant as active/deactive",
    )

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """Inherited method to get domain from student transportation"""
        if self._context.get("name"):
            student_obj = self.env["student.student"]
            student_rec = student_obj.browse(self._context.get("name"))
            for student_data in student_rec:
                args.append(
                    (
                        "id",
                        "in",
                        [
                            transport_id.id
                            for transport_id in student_data.transport_ids
                        ],
                    )
                )
        return super(TransportParticipant, self)._search(
            args,
            offset=offset,
            limit=limit,
            count=count,
            access_rights_uid=access_rights_uid,
        )

    def set_over(self):
        """Method to change state to over"""
        self.state = "over"

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state == "running":
                raise ValidationError(_("You cannot delete record in running state!."))
        return super(TransportParticipant, self).unlink()


class StudentTransports(models.Model):
    """for root detail."""

    _name = "student.transport"
    _description = "Student Transport Information"

    @api.depends("trans_participants_ids")
    def _compute_total_participants(self):
        """Method to compute total participant"""
        for rec in self:
            rec.total_participantes = len(rec.trans_participants_ids)

    name = fields.Char(
        "Transport Route Name",
        required=True,
        help="Enter Transport Route Name",
    )
    start_date = fields.Date(required=True, help="Enter start date")
    contact_per_id = fields.Many2one(
        "res.partner", "Contact Person", help="Contact Person"
    )
    end_date = fields.Date(required=True, help="Enter end date")
    total_participantes = fields.Integer(
        compute="_compute_total_participants",
        string="Total Participants",
        readonly=True,
        help="Total participant",
    )
    trans_participants_ids = fields.Many2many(
        "transport.participant",
        "transport_participant_rel",
        "participant_id",
        "transport_id",
        "Participants",
        readonly=True,
        help="Enter participant",
    )
    trans_vehicle_ids = fields.Many2many(
        "fleet.vehicle",
        "transport_vehicle_rel",
        "vehicle_id",
        "transport_id",
        "vehicles",
        help="Select transport vehicles",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("close", "Close")],
        readonly=True,
        default="draft",
        help="State of student transport",
    )
    amount = fields.Float("Transport Amount")

    def transport_open(self):
        """Method to change state open."""
        self.state = "open"

    def transport_close(self):
        """Method to change state to close."""
        self.state = "close"

    @api.model
    def participant_expire(self):
        """Schedular to change in participant state when registration date.

        is over.
        """
        current_date = fields.Date.today()
        trans_parti_obj = self.env["transport.participant"]
        for partitcipants in trans_parti_obj.search(
            [("tr_end_date", "<", current_date)]
        ):
            partitcipants.state = "over"

    @api.constrains("start_date", "end_date")
    def check_dates(self):
        """Constraint ot check start/end date and duration"""
        for rec in self:
            new_dt = fields.Date.context_today(self)
            delta = rec.end_date - rec.start_date
            if rec.start_date < new_dt or rec.end_date < new_dt:
                raise ValidationError(
                    _(
                        "Start date or End date should be greater"
                        " than or equal to the current date!"
                    )
                )

            if rec.start_date > rec.end_date:
                raise ValidationError(_("Start date should be less than end date!"))
            if delta.days < 30:
                raise ValidationError(_("Enter duration of month!"))

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state == "open":
                raise ValidationError(
                    _("You can delete record in draft state or cancel state only!")
                )
        return super(StudentTransports, self).unlink()


class StudentStudent(models.Model):
    _inherit = "student.student"
    _description = "Student Information"

    transport_ids = fields.Many2many(
        "transport.participant",
        "std_transport",
        "trans_id",
        "stud_id",
        "Transport",
        help="Student transportation",
    )

    def set_alumni(self):
        """Override method to make record of student transport active false.

        when student is set to alumni state.
        """
        trans_student_obj = self.env["transport.participant"]
        trans_regi_obj = self.env["transport.registration"]
        for rec in self:
            trans_student_rec = trans_student_obj.search([("name", "=", rec.id)])
            trans_regi_rec = trans_regi_obj.search([("student_id", "=", rec.id)])
            if trans_regi_rec:
                trans_regi_rec.state = "cancel"
            if trans_student_rec:
                trans_student_rec.active = False
        return super(StudentStudent, self).set_alumni()


class TransportRegistration(models.Model):
    """for registration."""

    _name = "transport.registration"
    _description = "Transport Registration"

    @api.depends("state")
    def _compute_get_user_groups(self):
        """Method to compute transport user boolean field"""
        transport_user_group = self.env.ref(
            "school_transport.group_transportation_user"
        )
        grps = [group.id for group in self.env.user.groups_id]
        self.transport_user = False
        if transport_user_group.id in grps:
            self.transport_user = True

    @api.depends("monthly_amount", "registration_month")
    def _compute_transport_fees(self):
        """Method to compute transport fees"""
        for rec in self:
            rec.transport_fees = rec.monthly_amount * rec.registration_month

    name = fields.Many2one(
        "student.transport",
        "Transport Route Name",
        domain=[("state", "=", "open")],
        required=True,
        help="Enter transport Route Name",
    )
    student_id = fields.Many2one(
        "student.student", "Student Name", required=True, help="Student Name"
    )
    reg_date = fields.Date(
        "Registration Date",
        readonly=True,
        help="Start Date of registration",
        default=fields.Date.context_today,
    )
    reg_end_date = fields.Date(
        "Registration End Date",
        readonly=True,
        help="Start Date of registration",
    )
    registration_month = fields.Integer("Registration For Months")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirm"),
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("cancel", "Cancel"),
        ],
        readonly=True,
        default="draft",
        help="State of the transport registration form",
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        "Vehicle No",
        required=True,
        help="Enter transport vehicle",
    )
    monthly_amount = fields.Float(help="Enter monthly amount")
    paid_amount = fields.Float(help="Amount Paid")
    tax_amount = fields.Float("Taxable Amount", help="Tax Amount")
    remain_amt = fields.Float("Due Amount", help="Amount Remaining")
    transport_fees = fields.Float(
        compute="_compute_transport_fees",
        help="Transport fees",
    )
    amount = fields.Float("Final Amount", readonly=True, help="Final amount")
    count_inv = fields.Integer(
        "Invoice Count", compute="_compute_invoice", help="Total invoice"
    )
    transport_user = fields.Boolean(
        compute="_compute_get_user_groups",
        string="Transport user",
        help="Activate/Deactivate as following user is transport user or not",
    )

    @api.constrains("student_id", "reg_date")
    def check_student_route(self):
        record = self.search(
            [
                ("id", "!=", self.id),
                ("student_id", "=", self.student_id.id),
                ("reg_date", "=", self.reg_date),
                ("state", "not in", ["paid", "cancel"]),
            ]
        )
        if record:
            raise ValidationError(_("Student already has different route"))

    @api.onchange("name")
    def onchange_name(self):
        """
        This onchange will take amount from student.transport and
        set monthly amount
        """
        self.monthly_amount = 0.0
        self.vehicle_id = False
        if self.name:
            self.monthly_amount = self.name.amount

    @api.model
    def create(self, vals):
        """Inherited create method to call onchange methods"""
        ret_val = super(TransportRegistration, self).create(vals)
        if ret_val:
            ret_val.onchange_registration_month()
        return ret_val

    def unlink(self):
        """Inherited method to check state at record deletion"""
        for rec in self:
            if rec.state in ["confirm", "pending", "paid"]:
                raise ValidationError(
                    _(
                        "You can delete record in unconfirm state and cancel "
                        "state only!"
                    )
                )
        return super(TransportRegistration, self).unlink()

    def transport_fees_pay(self):
        """Method to generate invoice of participant."""
        invoice_obj = self.env["account.move"]
        for rec in self:
            rec.state = "pending"
            partner = rec.student_id and rec.student_id.partner_id
            invoice = invoice_obj.create(
                {
                    "partner_id": partner.id,
                    "move_type": "out_invoice",
                    "transport_student_id": rec.id,
                }
            )
            journal = invoice.journal_id
            acct_journal_id = journal.default_account_id.id
            account_view_id = self.env.ref("account.view_move_form")
            invoice.invoice_line_ids = [
                (
                    0,
                    0,
                    {
                        "name": "Transport Fees",
                        "account_id": acct_journal_id,
                        "quantity": rec.registration_month,
                        "price_unit": rec.monthly_amount,
                    },
                )
            ]
            return {
                "name": _("Pay Transport Fees"),
                "view_mode": "form",
                "res_model": "account.move",
                "view_id": account_view_id.id,
                "type": "ir.actions.act_window",
                "nodestroy": True,
                "target": "current",
                "res_id": invoice.id,
                "context": {},
            }

    def view_invoice(self):
        """Method to view invoice of participant."""
        invoice_obj = self.env["account.move"]
        for rec in self:
            invoices = invoice_obj.search([("transport_student_id", "=", rec.id)])
            action = rec.env.ref("account.action_move_out_invoice_type").read()[0]
            if len(invoices) > 1:
                action["domain"] = [("id", "in", invoices.ids)]
            elif len(invoices) == 1:
                action["views"] = [(rec.env.ref("account.view_move_form").id, "form")]
                action["res_id"] = invoices.ids[0]
            else:
                action = {"type": "ir.actions.act_window_close"}
            return action

    def _compute_invoice(self):
        """Method to compute number of invoice of participant."""
        inv_obj = self.env["account.move"]
        for rec in self:
            rec.count_inv = inv_obj.search_count(
                [("transport_student_id", "=", rec.id)]
            )

    @api.onchange("registration_month")
    def onchange_registration_month(self):
        """Method to compute registration end date."""
        tr_start_date = fields.Date.today()
        tr_end_date = tr_start_date + relativedelta(months=self.registration_month)
        self.reg_end_date = tr_end_date

    def trans_regi_cancel(self):
        """Method to set state to cancel."""
        self.state = "cancel"

    def trans_regi_confirm(self):
        """Method to confirm registration."""
        trans_obj = self.env["student.transport"]
        prt_obj = self.env["student.student"]
        stu_prt_obj = self.env["transport.participant"]
        vehi_obj = self.env["fleet.vehicle"]
        for rec in self:
            # registration months must one or more then one
            if rec.registration_month <= 0:
                raise UserError(
                    _(
                        """Error!
Registration months must be 1 or more then one month!"""
                    )
                )
            # First Check Is there vacancy or not
            person = int(rec.vehicle_id.participant_count) + 1
            if rec.vehicle_id.seats < person:
                raise UserError(_("There is No More vacancy on this vehicle!"))

            rec.write({"state": "confirm", "remain_amt": rec.transport_fees})
            # calculate amount and Registration End date
            tr_start_date = rec.reg_date
            ed_date = rec.name.end_date
            tr_end_date = tr_start_date + relativedelta(months=rec.registration_month)
            if tr_end_date > ed_date:
                raise UserError(
                    _(
                        "For this much Months Registration is not Possible "
                        "as Root end date is Early!"
                    )
                )
            # make entry in Transport
            temp = stu_prt_obj.sudo().create(
                {
                    "stu_pid_id": str(rec.student_id.pid),
                    "amount": rec.monthly_amount,
                    "transport_id": rec.name.id,
                    "tr_end_date": tr_end_date,
                    "name": rec.student_id.id,
                    "months": rec.registration_month,
                    "tr_reg_date": rec.reg_date,
                    "state": "running",
                    "vehicle_id": rec.vehicle_id.id,
                }
            )
            # make entry in Transport vehicle.
            vehi_participants_list = []
            for prt in rec.vehicle_id.vehi_participants_ids:
                vehi_participants_list.append(prt.id)
            vehi_participants_list.append(temp.id)
            vehicle_rec = vehi_obj.browse(rec.vehicle_id.id)
            vehicle_rec.sudo().write(
                {"vehi_participants_ids": [(6, 0, vehi_participants_list)]}
            )
            # make entry in student.
            transport_list = []
            for root in rec.student_id.transport_ids:
                transport_list.append(root.id)
            transport_list.append(temp.id)
            student_rec = prt_obj.browse(rec.student_id.id)
            student_rec.sudo().write({"transport_ids": [(6, 0, transport_list)]})
            # make entry in transport.
            trans_participants_list = []
            for prt in rec.name.trans_participants_ids:
                trans_participants_list.append(prt.id)
            trans_participants_list.append(temp.id)
            stu_tran_rec = trans_obj.browse(rec.name.id)
            stu_tran_rec.sudo().write(
                {"trans_participants_ids": [(6, 0, trans_participants_list)]}
            )


class AccountInvoice(models.Model):
    _inherit = "account.move"

    transport_student_id = fields.Many2one(
        "transport.registration",
        string="Transport Student",
        help="Transport records",
    )


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def action_create_payments(self):
        """
        Override method to write paid amount in hostel student
        """
        res = super(AccountPaymentRegister, self).action_create_payments()
        invoice = False
        for rec in self:
            if self._context.get("active_model") == "account.move":
                invoice = self.env["account.move"].browse(
                    self._context.get("active_ids", [])
                )
            vals = {}
            if invoice.transport_student_id and invoice.payment_state == "paid":
                fees_payment = invoice.transport_student_id.paid_amount + rec.amount
                vals.update(
                    {
                        "state": "paid",
                        "paid_amount": fees_payment,
                        "remain_amt": 0.0,
                        "tax_amount": invoice.amount_tax,
                    }
                )
            elif invoice.transport_student_id and invoice.payment_state == "not_paid":
                fees_payment = invoice.transport_student_id.paid_amount + rec.amount
                vals.update(
                    {
                        "state": "pending",
                        "paid_amount": fees_payment,
                        "tax_amount": invoice.amount_tax,
                        "remain_amt": invoice.amount_residual,
                    }
                )
            invoice.transport_student_id.write(vals)
        return res
