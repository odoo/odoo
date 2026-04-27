# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AppointmentInviteHrRecruitment(models.Model):
    _inherit = "appointment.invite"

    applicant_id = fields.Many2one('hr.applicant', "Applicant",
        help="Link an applicant to the appointment invite created.\n"
            "Used when creating an invitation from the Meeting action in the applicant form view.")
