# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.osv.expression import AND


class HrRecruitmentPopulateWizard(models.TransientModel):
    _name = 'hr.recruitment.populate.wizard'
    _description = 'Populate Job Position Wizard'

    job_id = fields.Many2one('hr.job', default=lambda self: self.env.context.get('active_id'))
    skill_ids = fields.Many2many('hr.skill', string="Skills")
    categ_ids = fields.Many2many('hr.applicant.category', string="Tags")
    degree_id = fields.Many2one('hr.recruitment.degree', "Degree") # on hr.applicant: type_id
    availability = fields.Selection(
        selection=[
            ('now', 'Immediately'),
            ('quarter', 'In the next 3 months'),
            ('year', 'In the coming year'),
        ],
        required=True,
        default='now')

    def action_validate(self):
        self.ensure_one()
        domain = [('job_id', '=', False)]
        if self.skill_ids:
            domain = AND([domain, [('applicant_skill_ids.skill_id', 'in', self.skill_ids.ids)]])
        if self.categ_ids:
            domain = AND([domain, [('categ_ids', 'in', self.categ_ids.ids)]])
        if self.degree_id:
            domain = AND([domain, [('type_id', '=', self.degree_id.id)]])

        today = fields.Date.today()
        if self.availability == 'now':
            domain = AND([domain, ['|', ('availability', '=', False), ('availability', '<=', today)]])
        elif self.availability == 'quarter':
            domain = AND([domain, ['|', ('availability', '=', False), ('availability', '<=', today + relativedelta(months=3))]])
        else:
            domain = AND([domain, ['|', ('availability', '=', False), ('availability', '<=', today + relativedelta(years=1))]])

        reserve = self.env['hr.applicant'].search(domain)
        reserve.job_id = self.job_id
