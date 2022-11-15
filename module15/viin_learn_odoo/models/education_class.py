from odoo import fields, models


class EducationClass(models.Model):
    # _inherit = 'base.education'
    _name = 'education.class'
    description = 'Education Class'
    
    name = fields.Char(string='Name', required=True)
    school_id = fields.Many2one('education.school', string='School', required=True)
    teacher_ids = fields.Many2many('res.partner', string='Teachers')
    student_ids = fields.One2many('education.student', 'class_id', string='Students')
    
    def get_all_students(self):
        # Khởi tạo đối tượng education.student (đây là một recordset rỗng của model education.student)
        student = self.env['education.student']
        all_students = student.search([])
        print("All Students: ", all_students)

    def change_class_name(self):
        self.ensure_one()
        self.name = 'Class 12A1'

    def find_student(self):
        domain = ['|', ('name', 'ilike', 'John'), ('class_id.name', '=', '12A1')]
        students = self.search(domain)

    def create_classes(self):
        # Giá trị để tạo bản ghi student 01
        student_01 = {
            'name': 'Student 01',
        }
        # Giá trị để tạo bản ghi student 02
        student_02 = {
            'name': 'Student 02'
        }
        # Giá trị để tạo bản ghi lớp học
        class_value = {
            'name': 'Class 01',
            # Đồng thời tạo mới 2 học sinh
            'student_ids': [
                (0, 0, student_01),
                (0, 0, student_02)
            ]
        }
        record = self.env['education.class'].create(class_value)

    def add_student(self):
        self.ensure_one()
        self.write({
            'student_ids': [(0, 0, {
                'name': 'Student'
            })]
        })
       
