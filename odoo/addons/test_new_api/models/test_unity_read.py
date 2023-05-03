from odoo import models, fields

class Course(models.Model):
    _name = 'test_new_api.course'
    _description = 'a course'

    name = fields.Char('Name')
    lesson_ids = fields.One2many('test_new_api.lesson', 'course_id')
    author_id = fields.Many2one('test_new_api.person')
    private_field = fields.Char(groups="base.group_no_one")
    reference = fields.Reference(string='reference to lesson', selection='_selection_reference_model')
    m2o_reference_id = fields.Many2oneReference(string='reference to lesson too', model_field='m2o_reference_model')
    m2o_reference_model = fields.Char(string='reference to the model for m2o_reference')

    def _selection_reference_model(self):
        return [('test_new_api.lesson', None)]

class Lesson(models.Model):
    _name = 'test_new_api.lesson'
    _description = 'a lesson of a course (a day typically)'

    name = fields.Char('Name')
    course_id = fields.Many2one('test_new_api.course')
    attendee_ids = fields.Many2many('test_new_api.person', 'lesson_ids')
    teacher_id = fields.Many2one('test_new_api.person')
    date = fields.Date()

    def _compute_display_name(self):
        """
        use to check that a context has can still have an impact when reading the names of a many2one
        """
        for record in self:
            if 'special' in self.env.context:
                record.display_name = 'special ' + record.name
            else:
                record.display_name = record.name

class Person(models.Model):
    _name = 'test_new_api.person'
    _description = 'a person, can be an author, teacher or attendee of a lesson'

    name = fields.Char('Name')
    lesson_ids = fields.Many2many('test_new_api.lesson', 'course_id')
    employer_id = fields.Many2one('test_new_api.employer')

    def name_get(self):
        """
        use to check that a context has can still have an impact when reading the names of a many2one
        """
        return [(record.id,
                 ("particular " if 'particular' in self.env.context else "") +
                 record.name +
                 (" special" if 'special' in self.env.context else ""))
                for record in self]

class Employer(models.Model):
    _name = 'test_new_api.employer'
    _description = 'the employer of a person'

    name = fields.Char('Name')
    employee_ids = fields.One2many('test_new_api.person', 'employer_id')
