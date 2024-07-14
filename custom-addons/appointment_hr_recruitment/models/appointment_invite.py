# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AppointmentInviteHrRecruitment(models.Model):
    _inherit = "appointment.invite"

    applicant_id = fields.Many2one('hr.applicant', "Applicant",
        help="Link an applicant to the appointment invite created.\n"
            "Used when creating an invitation from the Meeting action in the applicant form view.")

    def _get_meeting_categories_for_appointment(self):
        """ Add the interview category to the meeting created if linked to an applicant
            :return <calendar.event.type> recordset:
        """
        categ_ids = super()._get_meeting_categories_for_appointment()
        if self.applicant_id:
            categ_ids += self.env.ref('hr_recruitment.categ_meet_interview', raise_if_not_found=False)
        return categ_ids
