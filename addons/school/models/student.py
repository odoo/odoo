# See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules import get_module_resource

from . import school

# from lxml import etree
# added import statement in try-except because when server runs on
# windows operating system issue arise because this library is not in Windows.
try:
    from odoo.tools import image_colorize
except Exception:
    image_colorize = False


class StudentStudent(models.Model):
    """Defining a student information."""

    _name = "student.student"
    _table = "student_student"
    _description = "Student Information"
    _inherit = ["mail.thread", "mail.activity.mixin"]

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
        """Method to get student of parent having group teacher"""
        teacher_group = self.env.user.has_group("school.group_school_teacher")
        parent_grp = self.env.user.has_group("school.group_school_parent")
        login_user_rec = self.env.user
        name = self._context.get("student_id")
        if name and teacher_group and parent_grp:
            parent_login_stud_rec = self.env["school.parent"].search(
                [("partner_id", "=", login_user_rec.partner_id.id)]
            )
            childrens = parent_login_stud_rec.student_id
            args.append(("id", "in", childrens.ids))
        return super(StudentStudent, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )

    @api.depends("date_of_birth")
    def _compute_student_age(self):
        """Method to calculate student age"""
        current_dt = fields.Date.today()
        for rec in self:
            rec.age = 0
            if rec.date_of_birth and rec.date_of_birth < current_dt:
                start = rec.date_of_birth
                age_calc = (current_dt - start).days / 365
                # Age should be greater than 0
                if age_calc > 0.0:
                    rec.age = age_calc

    @api.model
    def _default_image(self):
        """Method to get default Image"""
        image_path = get_module_resource("hr", "static/src/img", "default_image.png")
        return base64.b64encode(open(image_path, "rb").read())

    @api.depends("state")
    def _compute_teacher_user(self):
        """Compute teacher boolean field if user form teacher group"""
        teacher = self.env.user.has_group("school.group_school_teacher")
        for rec in self:
            rec.teachr_user_grp = False
            if teacher and rec.state == "done":
                rec.teachr_user_grp = True

    @api.model
    def check_current_year(self):
        """Method to get default value of logged in Student"""
        res = self.env["academic.year"].search([("current", "=", True)])
        if not res:
            raise ValidationError(
                _(
                    "There is no current Academic Year defined! Please "
                    "contact Administator!"
                )
            )
        return res.id

    family_con_ids = fields.One2many(
        "student.family.contact",
        "family_contact_id",
        string="Family Contact Detail",
        states={"done": [("readonly", True)]},
        help="Select the student family contact",
    )
    user_id = fields.Many2one(
        "res.users",
        string="User ID",
        ondelete="cascade",
        required=True,
        delegate=True,
        help="Select related user of the student",
    )
    student_name = fields.Char(
        string="Student Name",
        related="user_id.name",
        store=True,
        readonly=True,
        help="Student Name",
    )
    pid = fields.Char(
        string="Student ID",
        required=True,
        default=lambda self: _("New"),
        help="Personal IDentification Number",
    )
    reg_code = fields.Char(string="Registration Code", help="Student Registration Code")
    student_code = fields.Char(help="Enter student code")
    contact_phone = fields.Char(string="Phone no.", help="Enter student phone no.")
    contact_mobile = fields.Char(string="Mobile no", help="Enter student mobile no.")
    roll_no = fields.Integer("Roll No.", readonly=True, help="Enter student roll no.")
    leaving_certificate = fields.Char(string="leaving_certificate")
    photo = fields.Binary(default=_default_image, help="Attach student photo")
    year = fields.Many2one(
        "academic.year",
        "Academic Year",
        readonly=True,
        default=check_current_year,
        help="Select academic year",
        tracking=True,
    )
    cast_id = fields.Many2one(
        "student.cast", "Religion/Caste", help="Select student cast"
    )
    relation = fields.Many2one(
        "student.relation.master", help="Select student relation"
    )
    country_id = fields.Many2one("res.country", string="Nationality")

    admission_date = fields.Date(
        default=fields.Date.today(),
        help="Enter student admission date",
    )
    leave_date = fields.Date(help="Enter student leave date")
    middle = fields.Char(
        "Middle Name",
        required=True,
        states={"done": [("readonly", True)]},
        help="Enter student middle name",
    )
    last = fields.Char(
        "Surname",
        required=True,
        states={"done": [("readonly", True)]},
        help="Enter student last name",
    )
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female")],
        states={"done": [("readonly", True)]},
        help="Select student gender",
    )
    date_of_birth = fields.Date(
        "BirthDate",
        required=True,
        states={"done": [("readonly", True)]},
        help="Enter student date of birth",
    )
    mother_tongue = fields.Many2one(
        "mother.toungue", help="Select student mother tongue"
    )
    age = fields.Integer(
        compute="_compute_student_age",
        readonly=True,
        help="Enter student age",
    )
    maritual_status = fields.Selection(
        [("unmarried", "Unmarried"), ("married", "Married")],
        "Marital Status",
        states={"done": [("readonly", True)]},
        help="Select student maritual status",
    )
    reference_ids = fields.One2many(
        "student.reference",
        "reference_id",
        "References",
        states={"done": [("readonly", True)]},
        help="Enter student references",
    )
    previous_school_ids = fields.One2many(
        "student.previous.school",
        "previous_school_id",
        "Previous School Detail",
        states={"done": [("readonly", True)]},
        help="Enter student school details",
    )
    doctor = fields.Char(
        "Doctor Name",
        states={"done": [("readonly", True)]},
        help="Enter doctor name for student medical details",
    )
    designation = fields.Char(help="Enter doctor designation")
    doctor_phone = fields.Char(string="Contact No.", help="Enter doctor phone")
    blood_group = fields.Char(help="Enter student blood group")
    height = fields.Float(help="Hieght in C.M")
    weight = fields.Float(help="Weight in K.G")
    eye = fields.Boolean("Eyes", help="Eye for medical info")
    ear = fields.Boolean("Ears", help="Eye for medical info")
    nose_throat = fields.Boolean("Nose & Throat", help="Nose & Throat for medical info")
    respiratory = fields.Boolean(help="Respiratory for medical info")
    cardiovascular = fields.Boolean(help="Cardiovascular for medical info")
    neurological = fields.Boolean(help="Neurological for medical info")
    muskoskeletal = fields.Boolean(help="Musculoskeletal for medical info")
    dermatological = fields.Boolean(help="Dermatological for medical info")
    blood_pressure = fields.Boolean(help="Blood pressure for medical info")
    remark = fields.Text(
        states={"done": [("readonly", True)]},
        help="Remark can be entered if any",
    )
    school_id = fields.Many2one(
        "school.school",
        "School",
        states={"done": [("readonly", True)]},
        help="Select school",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("terminate", "Terminate"),
            ("cancel", "Cancel"),
            ("alumni", "Alumni"),
        ],
        "Status",
        readonly=True,
        default="draft",
        tracking=True,
        help="State of the student registration form",
    )
    history_ids = fields.One2many(
        "student.history",
        "student_id",
        "History",
        help="Enter student history",
    )
    certificate_ids = fields.One2many(
        "student.certificate",
        "student_id",
        "Certificate",
        help="Enter student certificates",
    )
    student_discipline_line = fields.One2many(
        "student.descipline",
        "student_id",
        "Descipline",
        help="""Enter student descipline info""",
    )
    document = fields.One2many(
        "student.document",
        "doc_id",
        "Documents",
        help="Attach student documents",
    )
    description = fields.One2many("student.description", "des_id", help="Description")
    award_list = fields.One2many(
        "student.award",
        "award_list_id",
        help="Student award list",
    )
    stu_name = fields.Char(
        "First Name",
        related="user_id.name",
        readonly=True,
        help="Enter student first name",
        tracking=True,
    )
    Acadamic_year = fields.Char(
        "Year",
        related="year.name",
        help="Academic Year",
        readonly=True,
        tracking=True,
    )
    division_id = fields.Many2one(
        "standard.division",
        "Division",
        help="Select student standard division",
        tracking=True,
    )
    medium_id = fields.Many2one(
        "standard.medium",
        "Medium",
        help="Select student standard medium",
        tracking=True,
    )
    standard_id = fields.Many2one(
        "school.standard",
        "Class",
        help="Select student standard",
        tracking=True,
    )
    parent_id = fields.Many2many(
        "school.parent",
        "students_parents_rel",
        "student_id",
        "students_parent_id",
        "Parent(s)",
        states={"done": [("readonly", True)]},
        help="Enter student parents",
    )
    terminate_reason = fields.Text(
        "Reason", help="Enter student terminate reason", tracking=True
    )
    active = fields.Boolean(
        default=True, help="Activate/Deactivate student record", tracking=True
    )
    teachr_user_grp = fields.Boolean(
        "Teacher Group",
        compute="_compute_teacher_user",
        help="Activate/Deactivate teacher group",
    )
    subject_id = fields.Many2one("subject.subject", "Subject", help="Subject")

    # @api.model
    # def get_views(self, views, options=None):
    #     res = super().get_views(views, options)
    #     if res["views"].get("list", {}):
    #         reports = res["views"].get("list", {}).get("toolbar").get("print")
    #         form_reports = res["views"].get("form", {}).get("toolbar").get("print")
    #         index = 0
    #         rem_index = ""
    #         for report in reports:
    #             if not self._context.get(
    #                 "is_student_alumni_terminate", False
    #             ) and self.env.ref(
    #                 "school.report_student_student_leaving_certificate"
    #             ).id == report.get(
    #                 "id"
    #             ):
    #                 rem_index = index
    #             index += 1
    #         if rem_index:
    #             reports.pop(int(rem_index))
    #             form_reports.pop(int(rem_index))
    #     return res

    @api.model
    def create(self, vals):
        """Method to create user when student is created"""
        if vals.get("pid", _("New")) == _("New"):
            vals["pid"] = self.env["ir.sequence"].next_by_code("student.student") or _(
                "New"
            )
        if vals.get("pid", False):
            vals["login"] = vals["pid"]
            vals["password"] = vals["pid"]
        else:
            raise UserError(_("Error! PID not valid so record will not be saved."))
        if vals.get("company_id", False):
            company_vals = {"company_ids": [(4, vals.get("company_id"))]}
            vals.update(company_vals)
        if vals.get("email"):
            school.emailvalidation(vals.get("email"))
        res = super(StudentStudent, self).create(vals)
        teacher = self.env["school.teacher"]
        for data in res.parent_id:
            for record in teacher.search([("stu_parent_id", "=", data.id)]):
                record.write({"student_id": [(4, res.id, None)]})
        # Assign group to student based on condition
        emp_grp = self.env.ref("base.group_user")
        if res.state == "draft":
            admission_group = self.env.ref("school.group_is_admission")
            new_grp_list = [admission_group.id, emp_grp.id]
            res.user_id.write({"groups_id": [(6, 0, new_grp_list)]})
        elif res.state == "done":
            done_student = self.env.ref("school.group_school_student")
            group_list = [done_student.id, emp_grp.id]
            res.user_id.write({"groups_id": [(6, 0, group_list)]})
        return res

    def write(self, vals):
        """Inherited method write to assign
        student to their respective teacher"""
        teacher = self.env["school.teacher"]
        if vals.get("parent_id"):
            for parent in vals.get("parent_id")[0][2]:
                for data in teacher.search([("stu_parent_id", "=", parent)]):
                    data.write({"student_id": [(4, self.id)]})
        return super(StudentStudent, self).write(vals)

    @api.constrains("date_of_birth")
    def check_age(self):
        """Method to check age should be greater than 6"""
        if self.date_of_birth:
            start = self.date_of_birth
            age_calc = (fields.Date.today() - start).days / 365
            # Check if age less than required age
            if age_calc < self.school_id.required_age:
                raise ValidationError(
                    _(
                        "Age of student should be greater than %s years!"
                        % (self.school_id.required_age)
                    )
                )

    @api.constrains("admission_date", "leave_date")
    def _check_date(self):
        if self.leave_date and self.admission_date > self.leave_date:
            raise ValidationError(
                _("The leave date should be greater than the start date")
            )

    def set_to_draft(self):
        """Method to change state to draft"""
        self.state = "draft"

    def set_alumni(self):
        """Method to change state to alumni"""
        for rec in self:
            rec.state = "alumni"
            rec.standard_id._compute_total_student()
            rec.active = False
            rec.user_id.active = False
            rec.leave_date = fields.Date.today()

    def set_done(self):
        """Method to change state to done"""
        self.state = "done"

    def admission_draft(self):
        """Set the state to draft"""
        self.state = "draft"

    def set_terminate(self):
        """Set the state to terminate"""
        self.state = "terminate"

    def cancel_admission(self):
        """Set the state to cancel."""
        self.state = "cancel"

    def reset_to_draft(self):
        """Set the state to cancel."""
        self.state = "draft"

    def admission_done(self):
        """Method to confirm admission"""
        school_standard_obj = self.env["school.standard"]
        ir_sequence = self.env["ir.sequence"]
        student_group = self.env.ref("school.group_school_student")
        emp_group = self.env.ref("base.group_user")
        for rec in self:
            if not rec.standard_id:
                raise ValidationError(_("Please select class!"))
            if rec.standard_id.remaining_seats < 0:
                raise ValidationError(
                    _("Seats of class %s are full") % rec.standard_id.standard_id.name
                )
            domain = [("school_id", "=", rec.school_id.id)]
            # Checks the standard if not defined raise error
            if not school_standard_obj.search(domain):
                raise UserError(_("Warning! The standard is not defined in school!"))
            # Assign group to student
            rec.user_id.write({"groups_id": [(6, 0, [emp_group.id, student_group.id])]})
            # Assign roll no to student
            number = 1
            for rec_std in rec.search(domain):
                rec_std.roll_no = number
                number += 1
            # Assign registration code to student
            reg_code = ir_sequence.next_by_code("student.registration")
            registation_code = (
                str(rec.school_id.state_id.name)
                + str("/")
                + str(rec.school_id.city)
                + str("/")
                + str(rec.school_id.name)
                + str("/")
                + str(reg_code)
            )
            stu_code = ir_sequence.next_by_code("student.code")
            student_code = (
                str(rec.school_id.code)
                + str("/")
                + str(rec.year.code)
                + str("/")
                + str(stu_code)
            )
            rec.write(
                {
                    "state": "done",
                    "admission_date": fields.Date.today(),
                    "student_code": student_code,
                    "reg_code": registation_code,
                }
            )
            template = (
                self.env["mail.template"]
                .sudo()
                .search([("name", "ilike", "Admission Confirmation")], limit=1)
            )
            if template:
                for user in rec.parent_id:
                    subject = _("About Admission Confirmation")
                    if user.email:
                        body = (
                            """
                        <div>
                            <p>Dear """
                            + str(user.display_name)
                            + """,
                            <br/><br/>
                            Admission of """
                            + str(rec.display_name)
                            + """ has been confirmed in """
                            + str(rec.school_id.name)
                            + """.
                            <br></br>
                            Thank You.
                        </div>
                        """
                        )
                        template.send_mail(
                            rec.id,
                            email_values={
                                "email_from": self.env.user.email or "",
                                "email_to": user.email,
                                "subject": subject,
                                "body_html": body,
                            },
                            force_send=True,
                        )
        return True
