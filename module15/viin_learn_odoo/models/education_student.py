from _datetime import date

from odoo import fields, models, api
from odoo.exceptions import ValidationError

from odoo import _
from odoo.exceptions import UserError


class EducationStudent(models.Model):
    _name = 'education.student'
    _description = 'Education Student'
    
    name = fields.Char(string='Student Name', required=True, translate=True)
    student_code = fields.Char(string='Student Code', required=True, index=True, help="Student ID is unique")
    class_id = fields.Many2one('education.class', string='Class', ondelete="restrict")
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')], string='Gender', default='male')
    date_of_birth = fields.Date(string='Date of Birth')
    # age = fields.Integer(string='Age')
    age = fields.Integer(string='Age', compute='_compute_age', inverse='_inverse_age', search='_search_age',
                     store=False, 
                     compute_sudo=True)
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Internal Notes')
    description = fields.Html(string='Description', sanitize=True, strip_style=False)
    attached_file = fields.Binary('Attached File', groups='base.group_user')
    total_score = fields.Float(string='Total Score', digits='Score')
    write_date = fields.Datetime(string='Last Updated on')
    currency_id = fields.Many2one('res.currency', string='Currency')
    amount_paid = fields.Monetary('Amount Paid')
    
    school_id = fields.Many2one('education.school', string='School')
    school_code = fields.Char(related='school_id.code', string='School Code')
    school_address = fields.Char(related='school_id.address', string='School Address')
    
    state = fields.Selection(string='Status', selection=[('new', 'New'),
                                                         ('studying', 'Studying'),
                                                         ('off', 'Off')], default='new')
    
    dropout_reason = fields.Text(string='Dropout Reason')

    def action_dropout(self):
        return self.env.ref('viin_education.education_student_dropout_wizard_action').read()[0]
    
    _sql_constraints = [
   ('student_code_unique', 'unique(student_code)', "The student code must be unique!"),
   ('check_total_score', 'CHECK(total_score >= 0)', "The Total Score must be greater than 0!")
]

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        for r in self:
            if r.date_of_birth > fields.Date.today():
                raise ValidationError('Date of Birth must be in the past')
    
    @api.depends('date_of_birth')
    def _compute_age(self):
        curent_year = fields.Date.today().year
        for r in self:
            if r.date_of_birth:
                r.age = curent_year - r.date_of_birth.year
            else:
                r.age = 0
                
    def _inverse_age(self):
        for r in self:
            if r.age and r.date_of_birth:
                curent_year = fields.Date.today().year
                dob_year = curent_year - r.age
                dob_month = r.date_of_birth.month
                dob_day = r.date_of_birth.day
                date_of_birth = date(dob_year, dob_month, dob_day)
                r.date_of_birth = date_of_birth
                
    def _search_age(self, operator, value):
        new_year = fields.Date.today().year - value
        new_value = date(1, 1, new_year)
        # age > value => date_of_birth < new_value
        operator_map = {'>': '<', '>=': '<=', '<': '>', '<=': '>='}
        new_operator = operator_map.get(operator, operator)
        return [('date_of_birth', new_operator, new_value)]
    
    @api.model
    def is_allowed_state(self, current_state, new_state):
        allowed_states = [('new', 'studying'), ('studying', 'off'), ('off', 'studying'), ('new', 'off')]
        return (current_state, new_state) in allowed_states
    
    def change_student_state(self, state):
        for student in self:
            if student.is_allowed_state(student.state, state):
                student.state = state
            else:
                raise UserError(_("Changing student status from %s to %s is not allowed.") % (student.state, state))
    def change_to_new(self):
        self.change_student_state('new')

    def change_to_studying(self):
        self.change_student_state('studying')
    
    def change_to_off(self):
        self.change_student_state('off')
    
