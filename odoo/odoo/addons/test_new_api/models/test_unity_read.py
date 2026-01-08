# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
    attendee_ids = fields.Many2many('test_new_api.person', 'lesson_ids', context={'active_test': False})
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
    active = fields.Boolean(default=True)

    def _compute_display_name(self):
        """
        use to check that a context has can still have an impact when reading the names of a many2one
        """
        particular = "particular " if 'particular' in self.env.context else ""
        special = " special" if 'special' in self.env.context else ""
        for record in self:
            record.display_name = f"{particular}{record.name}{special}"


class Employer(models.Model):
    _name = 'test_new_api.employer'
    _description = 'the employer of a person'

    name = fields.Char('Name')
    employee_ids = fields.One2many('test_new_api.person', 'employer_id')
    all_employee_ids = fields.One2many('test_new_api.person', 'employer_id', context={'active_test': False})


class PersonAccount(models.Model):
    _name = 'test_new_api.person.account'
    _description = 'an account with credentials for a given person'
    _inherits = {'test_new_api.person': 'person_id'}

    person_id = fields.Many2one('test_new_api.person', required=True, ondelete='cascade')
    login = fields.Char()
