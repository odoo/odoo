# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, fields, models
from odoo.exceptions import UserError

class L10nLuGenerateSalesReport(models.TransientModel):
    """
    This wizard is used to generate an xml EC Sales report for Luxembourg
    according to the xml 2.0 standard.
    """
    _inherit = 'l10n_lu.generate.xml'
    _name = 'l10n_lu.generate.vat.intra.report'
    _description = 'Generate Sales Report'

    l10n_lu_stored_report_ids = fields.Many2many(
        comodel_name="l10n_lu.stored.intra.report",
        domain="[('company_id', '=', allowed_company_ids[0])]",
        relation="l10n_lu_generate_intra_report_l10n_lu_stored_intra_report_rel")
    save_report = fields.Boolean(string="Store generated report", default=False)

    def _lu_get_declarations(self, declaration_template_values):
        report_generation_options = self.env.context['report_generation_options']
        # check codes: it is not possible to save a declaration that only contains 'L' code (sales of goods)
        # but not 'T' code (triangular sales), since they belong to the same declaration;
        # still, it is possible to export it
        selected = [code.get('name') for code in report_generation_options.get('intrastat_code', []) if code.get('selected')]
        if ('L' in selected) != ('T' in selected) and self.save_report:
            raise UserError(_("The report can't be saved, because it isn't a valid eCDF declaration. "
                              "Either both 'L' and 'T' codes should be selected, or none of them"))
        comparison_files = [(d.attachment_id.name, base64.b64decode(d.attachment_id.datas)) for d in self.l10n_lu_stored_report_ids]
        ec_sales_report = self.env.ref('l10n_lu_reports.lux_ec_sales_report')
        forms, year, period, codes = self.env[ec_sales_report.custom_handler_model_name].get_xml_2_0_report_values(report_generation_options, comparison_files)
        declarations = {'declaration_singles': {'forms': forms}, 'declaration_groups': []}
        declarations.update(declaration_template_values)
        return {'declarations': [declarations], 'year': year, 'period': period, 'codes': codes}

    def _save_xml_report(self, declarations_data, lu_template_values, filename):
        # Overridden to allow saving the report as a 'l10n_lu.stored.intra.report' (for future comparisons)
        super()._save_xml_report(declarations_data, lu_template_values, filename)

        if not self.save_report:
            return
        attachment = self.env['ir.attachment'].create({
            'name': self.filename,
            'company_id': self.env.company.id,
            'mimetype': 'application/xml',
            'datas': self.report_data,
            'description': "Report filename: " + self.filename,
        })
        self.env['l10n_lu.stored.intra.report'].create({
            'attachment_id': attachment.id,
            'year': declarations_data['year'],
            'period': declarations_data['period'],
            'codes': declarations_data['codes'],
            'company_id': self.env.company.id,
        })
