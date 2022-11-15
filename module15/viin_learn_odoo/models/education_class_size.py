from odoo import fields, models
from odoo.exceptions import UserError


class EducationClass(models.Model):
    _inherit = 'education.class'

    max_student = fields.Integer(string='Max Student', default=20)

    def add_student(self):
        # Kiểm tra max student trước khi thực hiện
        if len(self.student_ids) > self.max_student:
            raise UserError('The number of students has exceeded %s' % self.max_student)
        # Gọi lại nội dung phương thức cha
        super(EducationClass, self).add_student()