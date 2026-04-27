# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    voes = fields.Char(string="VOES Number", help="Used for companies outside EU that want to make use of OSS")
    ioss = fields.Char(string="IOSS Number", help="Identification number for companies that import goods and services into the EU. For use in OSS reports.")
    intermediary_no = fields.Char(string="Intermediary Number", help="Used for companies outside EU that import into the EU via an intermediary for OSS taxes")

    def _get_tax_periodicity(self, report):
        if report == self.env.ref('l10n_eu_oss_reports.oss_sales_report'):
            return 'trimester'
        elif report == self.env.ref('l10n_eu_oss_reports.oss_imports_report'):
            return 'monthly'
        return super()._get_tax_periodicity(report)

    def _get_closing_report_for_tax_closing_move(self, report, fpos):
        # Since the OSS reports are considered as a tax report but need other moves, we need to specify the report
        if report.availability_condition == 'oss':
            return report
        return super()._get_closing_report_for_tax_closing_move(report, fpos)
