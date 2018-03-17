# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class RejectReason(models.TransientModel):
    _name = "reject.reason"

    reasons = fields.Text('Reject Reason')

    @api.multi
    def save_reason(self):
        student_assignment = self.env['school.student.assignment']
        for rec in self:
            std_id = rec._context.get('active_id')
            student = student_assignment.browse(std_id)
            if student:
                student.write({'state': 'reject',
                               'rejection_reason': rec.reasons or ''})
        return True
