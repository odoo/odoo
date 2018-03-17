from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'
    current_academic_year = fields.Many2one('school.academic.year', 'Current Academic Year')
    school_starts = fields.Float('School Starts at', default=8.00)
    school_ends = fields.Float('School Ends at', default=2.00)
    late_time = fields.Float('Consider Late after', default=9.00)
    minimum_age = fields.Integer('Minimum Student Age')
    maximum_age = fields.Integer('Maximum Student Age')
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default='primary', string='School Type')

