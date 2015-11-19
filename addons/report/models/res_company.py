# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    paperformat_id = fields.Many2one('report.paperformat', string='Paper format')

    def init(self):
        # set a default paperformat based on rml one.

        companies = self.sudo().search([('paperformat_id', '=', False)])

        A4_paperformat = self.env.ref('report.paperformat_euro', False)
        US_paperformat = self.env.ref('report.paperformat_us', False)
        EUR_paperformat = self.env.ref('report.paperformat_euro', False)

        paperformat_dict = {
                'a4': A4_paperformat and A4_paperformat.id or False,
                'us_letter': US_paperformat and US_paperformat.id or False,
        }
        for company in companies:
            paperformat_id = paperformat_dict.get(company.rml_paper_format) or EUR_paperformat and EUR_paperformat.id
            if paperformat_id:
                company.write({'paperformat_id': paperformat_id})

        sup = super(ResCompany, self)
        if hasattr(sup, 'init'):
            sup.init()

    def _prepare_report_view_action(self, template):
        template_id = self.env.ref(template, False).id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': template_id,
        }

    @api.multi
    def edit_external_header(self):
        return self._prepare_report_view_action('report.external_layout_header')

    @api.multi
    def edit_external_footer(self):
        return self._prepare_report_view_action('report.external_layout_footer')

    @api.multi
    def edit_internal_header(self):
        return self._prepare_report_view_action('report.internal_layout')
