# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

import base64

class L10nChMasterDataReport(models.Model):
    _name = 'l10n.ch.master.data.report'
    _description = 'Swiss Master Data Report'

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)
    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], required=True, default=lambda self: str((fields.Date.today()).month))

    master_report_pdf_file = fields.Binary('Master Report', readonly=True, attachment=False)
    master_report_pdf_filename = fields.Char()

    wage_type_pdf_file = fields.Binary('Wage Type Report', readonly=True, attachment=False)
    wage_type_pdf_filename = fields.Char()

    def action_generate_pdf(self):
        company = self.company_id

        avs_records = company.l10n_ch_avs_institution_ids
        caf_records = company.l10n_ch_caf_institution_ids
        laa_records = company.l10n_ch_laa_institution_ids
        laac_records = company.l10n_ch_laac_institution_ids
        ijm_records = company.l10n_ch_ijm_institution_ids
        lpp_records = company.l10n_ch_lpp_institution_ids
        work_locations = company.l10n_ch_work_location_ids
        source_tax_institutions = company.l10n_ch_st_institution_ids
        salary_rules = self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').rule_ids.filtered(lambda r: r.l10n_ch_code).sorted('l10n_ch_code')
        
        master_report_data = {
            'doc': {
                'company': company,
                'avs_records': avs_records,
                'caf_records': caf_records,
                'laa_records': laa_records,
                'laac_records': laac_records,
                'ijm_records': ijm_records,
                'lpp_records': lpp_records,
                'work_locations': work_locations,
                'source_tax_institutions': source_tax_institutions,
            },
            'year': self.year,
            'month': self.month
        }
        
        wage_type_data = {
            'doc': {
                'company': company,
                'salary_rules': salary_rules
            },
            'year': self.year,
        }

        filename = 'master_data_%s-%s.pdf' % (self.year, self.month.zfill(2))
        master_report, _ = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            self.env.ref('l10n_ch_hr_payroll_elm_transmission.action_l10n_ch_company_master_data_report'),
            res_ids=self.ids, data=master_report_data)

        self.master_report_pdf_filename = filename
        self.master_report_pdf_file = base64.encodebytes(master_report)

        filename = 'wage_types_%s-%s.pdf' % (self.year, self.month.zfill(2))
        wage_type_report, _ = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            self.env.ref('l10n_ch_hr_payroll_elm_transmission.action_l10n_ch_company_wage_type_report'),
            res_ids=self.ids, data=wage_type_data)

        self.wage_type_pdf_filename = filename
        self.wage_type_pdf_file = base64.encodebytes(wage_type_report)
