# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    def _create_dashboard_notes(self):
        note = self.env['ir.qweb']._render('hr_payroll.hr_payroll_note_demo_content', {'date_today': fields.Date.today().strftime(self.env['res.lang']._lang_get(self.env.user.lang).date_format)})
        self.env['hr.payroll.note'].sudo().create([{
            'company_id': company.id,
            'name': _('Note'),
            'note': note,
        } for company in self])

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._create_dashboard_notes()
        return companies
