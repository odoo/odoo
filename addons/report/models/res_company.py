# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    paperformat_id = fields.Many2one('report.paperformat', 'Paper format')
    report_footer_default = fields.Html('Standard Report Foorter', compute='_compute_report_footer_default', readonly=True)

    @api.multi
    def _compute_report_footer_default(self):
        for company in self:
            company.report_footer_default = self.env['ir.ui.view'].render_template('report.external_layout_footer_default', {
                'company': company,
            })

    @api.model_cr
    def init(self):

        # set a default paperformat based on rml one.

        for company in self.search([('paperformat_id', '=', False)]):
            paperformat_euro = self.env.ref('report.paperformat_euro', False)
            paperformat_us = self.env.ref('report.paperformat_us', False)
            paperformat_id = {
                'a4': paperformat_euro and paperformat_euro.id or False,
                'us_letter': paperformat_us and paperformat_us.id or False,
            }.get(company.rml_paper_format) or paperformat_euro

            if paperformat_id:
                company.write({'paperformat_id': paperformat_id})

        sup = super(ResCompany, self)
        if hasattr(sup, 'init'):
            sup.init()

    @api.model
    def _prepare_report_view_action(self, template):
        template_id = self.env.ref(template)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': template_id.id,
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
