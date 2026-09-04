# See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SchoolTeacher(models.Model):
    """Defining a Teacher information."""

    _name = "school.teacher"
    _description = "Teacher Information"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    employee_id = fields.Many2one(
        "hr.employee",
        "Employee ID",
        ondelete="cascade",
        delegate=True,
        required=True,
        help="Enter related employee",
    )
    standard_id = fields.Many2one(
        "school.standard",
        "Responsibility of Academic Class",
        help="Standard for which the teacher responsible for.",
    )
    stand_id = fields.Many2one(
        "standard.standard",
        "Course",
        related="standard_id.standard_id",
        store=True,
        help="""Select standard which are assigned to teacher""",
    )
    subject_id = fields.Many2many(
        "subject.subject",
        "subject_teacher_rel",
        "teacher_id",
        "subject_id",
        "Course-Subjects",
        help="Select subject of teacher",
    )
    school_id = fields.Many2one("school.school", "Campus", help="Select school")
    category_ids = fields.Many2many(
        "hr.employee.category",
        "teacher_category_rel",
        "emp_id",
        "categ_id",
        "Tags",
        help="Select employee category",
    )
    department_id = fields.Many2one(
        "hr.department", "Department", help="Select department"
    )
    is_parent = fields.Boolean(help="Select this if it parent")
    stu_parent_id = fields.Many2one(
        "school.parent", "Related Parent", help="Enter student parent"
    )
    student_id = fields.Many2many(
        "student.student",
        "students_teachers_parent_rel",
        "teacher_id",
        "student_id",
        "Children",
        help="Select student",
    )
    phone_numbers = fields.Char(string="Phone Number", help="Student PH no")

    @api.onchange("standard_id")
    def _onchange_standard_id(self):
        for rec in self:
            rec.school_id = (
                rec.standard_id
                and rec.standard_id.school_id
                and rec.standard_id.school_id.id
                or False
            )

    @api.onchange("is_parent")
    def _onchange_isparent(self):
        """Onchange method for is parent"""
        self.stu_parent_id = False
        self.student_id = False

    @api.model
    def create(self, vals):
        """Inherited create method to assign value to users for delegation"""
        teacher_id = super(SchoolTeacher, self).create(vals)
        user_obj = self.env["res.users"]
        user_vals = {
            "name": teacher_id.name,
            "login": teacher_id.work_email,
            "email": teacher_id.work_email,
        }
        user_rec = user_obj.with_context(
            teacher_create=True, school_id=teacher_id.school_id.company_id.id
        ).create(user_vals)
        teacher_id.employee_id.write({"user_id": user_rec.id})
        #        if vals.get('is_parent'):
        #            self.parent_crt(teacher_id)
        return teacher_id

    @api.constrains("birthday")
    def _check_birthday(self):
        if self.birthday > date.today():
            raise ValidationError(_("Birthday cannot be greater than the current date"))

    # Removing this code because of issue faced due to email id of the
    # user is same for parent and Teacher, and system will not allow it.
    # now user shuld create Parent record first and then select it in
    # related parent in Teacher Profile. - Anu Patel (24/03/2021)
    #    def parent_crt(self, manager_id):
    #        """Method to create parent record based on parent field"""
    #        stu_parent = []
    #        if manager_id.stu_parent_id:
    #            stu_parent = manager_id.stu_parent_id
    #        if not stu_parent:
    #            emp_user = manager_id.employee_id
    #            students = [stu.id for stu in manager_id.student_id]
    #            parent_vals = {'name': manager_id.name,
    #                           'email': emp_user.work_email,
    #                           'user_ids': [(6, 0, [emp_user.user_id.id])],
    #                           'partner_id': emp_user.user_id.partner_id.id,
    #                           'student_id': [(6, 0, students)]}
    #            stu_parent = self.env['school.parent'].with_context(
    #                  ).create(parent_vals)
    #            manager_id.write({'stu_parent_id': stu_parent.id})
    #        user = stu_parent.user_ids
    #        user_rec = user[0]
    #        parent_grp_id = self.env.ref('school.group_school_parent')
    #        groups = parent_grp_id
    #        if user_rec.groups_id:
    #            groups = user_rec.groups_id
    #            groups += parent_grp_id
    #        group_ids = [group.id for group in groups]
    #        user_rec.write({'groups_id': [(6, 0, group_ids)]})

    def write(self, vals):
        """Inherited write method to assign groups based on parent field"""
        # if vals.get('is_parent'):
        #     self.parent_crt(self)
        if vals.get("student_id"):
            self.stu_parent_id.write({"student_id": vals.get("student_id")})
        if not vals.get("is_parent"):
            user_rec = self.employee_id.user_id
            parent_grp_id = self.env.ref("school.group_school_parent")
            if parent_grp_id in user_rec.groups_id:
                user_rec.write({"groups_id": [(3, parent_grp_id.id)]})
        if vals.get("name"):
            user_obj = self.employee_id.user_id
            user_vals = {"name": vals.get("name")}
            user_rec = user_obj.write(user_vals)
        return super(SchoolTeacher, self).write(vals)

    @api.onchange("address_id")
    def onchange_address_id(self):
        """Onchange method for address."""
        if self.address_id:
            self.work_phone = (self.address_id.phone or False,)
            self.mobile_phone = self.address_id.mobile or False

    @api.onchange("department_id")
    def onchange_department_id(self):
        """Onchange method for deepartment."""
        self.parent_id = (
            self.department_id
            and self.department_id.manager_id
            and self.department_id.manager_id.id
        ) or False

    @api.onchange("user_id")
    def onchange_user(self):
        """Onchange method for user."""
        if self.user_id:
            self.name = self.name or self.user_id.name
            self.work_email = self.user_id.email
            self.image = self.image or self.user_id.image

    @api.onchange("school_id")
    def onchange_school(self):
        """Onchange method for school."""
        partner = self.school_id.company_id.partner_id
        self.address_id = partner.id or False
        self.mobile_phone = partner.mobile or False
        self.work_location_id = partner.id or False
        self.work_email = partner.email or False
        phone = partner.phone or False
        self.work_phone = phone or False
        self.phone_numbers = phone or False
