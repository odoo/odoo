from odoo import models, fields, api


class SchoolSettings(models.TransientModel):
    _inherit = 'school.settings'
    current_academic_year = fields.Many2one('school.academic.year', 'Current Academic Year')
    school_starts = fields.Float('School Starts at', default=8.00)
    school_ends = fields.Float('School Ends at', default=2.00)
    late_time = fields.Float('Consider Late after', default=9.00)
    minimum_age = fields.Integer('Minimum Student Age')
    maximum_age = fields.Integer('Maximum Student Age')
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default='primary', string='School Type')

    @api.model
    def get_default_company_values(self, fields):
        company = self.env.user.company_id
        return {
            'current_academic_year': company.current_academic_year.id,
            'school_starts': company.school_starts,
            'school_ends': company.school_ends,
            'late_time': company.late_time,
            'minimum_age': company.minimum_age,
            'maximum_age': company.maximum_age,
            'school_type': company.school_type,
        }

    @api.one
    def set_company_values(self):
        company = self.env.user.company_id
        company.current_academic_year = self.current_academic_year
        company.school_starts = self.school_starts
        company.school_ends = self.school_ends
        company.late_time = self.late_time
        company.minimum_age = self.minimum_age
        company.maximum_age = self.maximum_age
        company.school_type = self.school_type
