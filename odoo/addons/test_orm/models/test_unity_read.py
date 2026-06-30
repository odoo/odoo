from odoo import fields, models


class TestOrmCourse(models.Model):
    _name = 'test_orm.course'
    _description = 'a course'

    name = fields.Char('Name')
    lesson_ids = fields.One2many('test_orm.lesson', 'course_id')
    author_id = fields.Many2one('test_orm.person')
    private_field = fields.Char(groups="base.group_no_one")
    reference = fields.Reference(string='reference to lesson', selection='_selection_reference_model')
    m2o_reference_id = fields.Many2oneReference(string='reference to lesson too', model_field='m2o_reference_model')
    m2o_reference_model = fields.Char(string='reference to the model for m2o_reference')

    def _selection_reference_model(self):
        return [('test_orm.lesson', None)]


class TestOrmLesson(models.Model):
    _name = 'test_orm.lesson'
    _description = 'a lesson of a course (a day typically)'

    name = fields.Char('Name')
    course_id = fields.Many2one('test_orm.course')
    attendee_ids = fields.Many2many('test_orm.person', 'lesson_ids', context={'active_test': False})
    teacher_id = fields.Many2one('test_orm.person')
    teacher_birthdate = fields.Date(related='teacher_id.birthday')
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


class TestOrmPerson(models.Model):
    _name = 'test_orm.person'
    _description = 'a person, can be an author, teacher or attendee of a lesson'

    name = fields.Char('Name')
    lesson_ids = fields.Many2many('test_orm.lesson', 'course_id')
    employer_id = fields.Many2one('test_orm.employer')
    birthday = fields.Date()
    active = fields.Boolean(default=True)

    def _compute_display_name(self):
        """
        use to check that a context has can still have an impact when reading the names of a many2one
        """
        particular = "particular " if 'particular' in self.env.context else ""
        special = " special" if 'special' in self.env.context else ""
        for record in self:
            record.display_name = f"{particular}{record.name}{special}"


class TestOrmEmployer(models.Model):
    _name = 'test_orm.employer'
    _description = 'the employer of a person'

    name = fields.Char('Name')
    employee_ids = fields.One2many('test_orm.person', 'employer_id')
    all_employee_ids = fields.One2many('test_orm.person', 'employer_id', context={'active_test': False})


class TestOrmPersonAccount(models.Model):
    _name = 'test_orm.person.account'
    _description = 'an account with credentials for a given person'
    _inherits = {'test_orm.person': 'person_id'}

    person_id = fields.Many2one('test_orm.person', required=True, ondelete='cascade')
    login = fields.Char()
    activation_date = fields.Date()
