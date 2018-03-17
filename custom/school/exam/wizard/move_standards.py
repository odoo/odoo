# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import except_orm


class MoveStandards(models.TransientModel):
    _inherit = 'move.standards'

    @api.multi
    def move_start(self):
        '''Method to change standard of student after he passes the exam'''
        academic_obj = self.env['academic.year']
        school_stand_obj = self.env['school.standard']
        standard_obj = self.env["standard.standard"]
        result_obj = self.env['exam.result']
        student_obj = self.env['student.student']
        stud_history_obj = self.env["student.history"]
        for rec in self:
            # search the done state students
            for stud in student_obj.search([('state', '=', 'done')]):
                stud_year_domain = [('academice_year_id',
                                     '=',
                                     rec.academic_year_id.id),
                                    ('student_id', '=', stud.id)]
                # check the student history for same academic year
                stud_year_ids = stud_history_obj.search(stud_year_domain)
                year_id = academic_obj.next_year(stud.year.sequence)
                if year_id and year_id != rec.academic_year_id.id:
                    continue
                if stud_year_ids:
                    raise except_orm(_('Please Select Next Academic year.'))
                else:
                    result_domain = [('standard_id', '=',
                                      stud.standard_id.id),
                                     ('standard_id.division_id',
                                      '=', stud.division_id.id),
                                     ('standard_id.medium_id',
                                      '=', stud.medium_id.id),
                                     ('student_id', '=', stud.id)]
                    # search the student result
                    result_data = result_obj.search(result_domain)
                    if result_data:
                        # find standard sequence no
                        std_seq = stud.standard_id.standard_id.sequence
                        if result_data.result == "Pass":
                            # find the next standard sequence no
                            next_class_id = standard_obj.next_standard(std_seq)
                            if next_class_id:
                                division = (stud.division_id.id or
                                            stud.standard_id.division_id.id or
                                            False)
                                domain = [('standard_id', '=', next_class_id),
                                          ('division_id', '=', division),
                                          ('school_id', '=',
                                                        stud.school_id.id),
                                          ('medium_id', '=',
                                                        stud.medium_id.id)]
                                # find the school standard record
                                next_stand = school_stand_obj.search(domain)
                                stud.write({'year': rec.academic_year_id.id,
                                            'standard_id': next_stand.id})
                        else:
                            raise except_orm(_('Student is not eligible'
                                               'for Next Standard.'))
        return True
#
