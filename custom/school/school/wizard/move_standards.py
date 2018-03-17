# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class MoveStandards(models.TransientModel):
    _name = 'move.standards'

    academic_year_id = fields.Many2one('academic.year', 'Academic Year',
                                       required=True)

    @api.multi
    def move_start(self):
        '''Code for moving student to next standard'''
        academic_obj = self.env['academic.year']
        school_stand_obj = self.env['school.standard']
        standard_obj = self.env["standard.standard"]
        stud_history_obj = self.env["student.history"]
        student_obj = self.env['student.student']
        for rec in self:
            for stud in student_obj.search([('state', '=', 'done')]):
                year_id = academic_obj.next_year(stud.year.sequence)
                # Check if academic year selected or not.
                if year_id != rec.academic_year_id.id:
                    continue
                standard_seq = stud.standard_id.standard_id.sequence
                next_class_id = standard_obj.next_standard(standard_seq)

                # Assign the academic year
                if next_class_id:
                    division = (stud.division_id.id or
                                stud.standard_id.division_id.id or False)
                    next_stand = school_stand_obj.search([('standard_id', '=',
                                                           next_class_id),
                                                          ('division_id', '=',
                                                           division),
                                                          ('school_id', '=',
                                                           stud.school_id.id),
                                                          ('medium_id', '=',
                                                           stud.medium_id.id)]
                                                         )
                    std_vals = {'year': rec.academic_year_id.id or False,
                                'standard_id': next_stand.id or False}
                    # Move student to next standard
                    stud.write(std_vals)
                    vals = {'student_id': stud.id,
                            'academice_year_id': stud.year.id,
                            'standard_id': stud.standard_id.id,
                            'medium_id': stud.medium_id.id,
                            'division_id': stud.division_id.id}
                    stud_history_obj.create(vals)
        return True
