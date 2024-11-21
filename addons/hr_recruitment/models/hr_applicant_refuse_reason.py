# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ApplicantRefuseReason(models.Model):
    _name = "hr.applicant.refuse.reason"
    _description = 'Refuse Reason of Applicant'
    _order = 'sequence'

    sequence = fields.Integer(copy=False, default=10)
    name = fields.Char('Description', required=True, translate=True)
    template_id = fields.Many2one('mail.template', string='Email Template', domain="[('model', '=', 'hr.applicant')]")
    active = fields.Boolean('Active', default=True)
