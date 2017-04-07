# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    paperformat_id = fields.Many2one('report.paperformat', 'Paper format', default=lambda self: self.env.ref('report.paperformat_euro', raise_if_not_found=False))
    external_report_layout = fields.Selection([
        ('background', 'Background'),
        ('boxed', 'Boxed'),
        ('clean', 'Clean'),
        ('standard', 'Standard'),
    ], string='Document Template')

    def open_company_edit_report(self):
        self.ensure_one()
        return self.env['base.config.settings'].open_company()

    def set_report_template(self):
        self.ensure_one()
        if self.env.context.get('report_template', False):
            self.external_report_layout = self.env.context['report_template']
        if self.env.context.get('default_report_name'):
            document = self.env.get(self.env.context['active_model']).browse(self.env.context['active_id'])
            return self.env['report'].get_action(document, self.env.context['default_report_name'], config=False)
        return False

    @api.model_cr
    def init(self):
        for company in self.search([('paperformat_id', '=', False)]):
            paperformat_euro = self.env.ref('report.paperformat_euro', False)
            if paperformat_euro:
                company.write({'paperformat_id': paperformat_euro.id})

        sup = super(ResCompany, self)
        if hasattr(sup, 'init'):
            sup.init()


