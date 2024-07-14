# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec')
class TestSwissdecCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ch'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.maxDiff = None
        mapped_payslips = cls.env.company._l10n_ch_generate_swissdec_demo_data()
        for indentifier, payslip in mapped_payslips.items():
            assert isinstance(indentifier, str)
            assert isinstance(payslip, cls.env['hr.payslip'].__class__)
            setattr(cls, indentifier, payslip)
        cls.company = cls.company_data['company']
        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].search([('name', '=', 'Test Calendar : 40 Hours/Week'), ('company_id', '=', cls.company.id)])
        cls.avs_1 = cls.env['l10n.ch.social.insurance'].search([('name', '=', 'AVS 2021')], limit=1)
        cls.laa_1 = cls.env['l10n.ch.accident.insurance'].search([('name', '=', "Backwork-Versicherungen")], limit=1)
        cls.laac_1 = cls.env['l10n.ch.additional.accident.insurance'].search([('name', '=', 'Backwork-Versicherungen')], limit=1)
        cls.ijm_1 = cls.env['l10n.ch.sickness.insurance'].search([('name', '=', 'Backwork-Versicherungen')], limit=1)
        cls.caf_lu_1 = cls.env['l10n.ch.compensation.fund'].search([("member_number", '=', '5676.3')], limit=1)

    def _validate_worked_days(self, payslip, results):
        error = []
        line_values = payslip._get_worked_days_line_values(set(results.keys()) | set(payslip.worked_days_line_ids.mapped('code')), ['number_of_days', 'number_of_hours', 'amount'])
        for code, (number_of_days, number_of_hours, amount) in results.items():
            payslip_line_value = line_values[code][payslip.id]['number_of_days']
            if float_compare(payslip_line_value, number_of_days, 2):
                error.append("Code: %s - Expected Number of Days: %s - Reality: %s" % (code, number_of_days, payslip_line_value))
            payslip_line_value = line_values[code][payslip.id]['number_of_hours']
            if float_compare(payslip_line_value, number_of_hours, 2):
                error.append("Code: %s - Expected Number of Hours: %s - Reality: %s" % (code, number_of_hours, payslip_line_value))
            payslip_line_value = line_values[code][payslip.id]['amount']
            if float_compare(payslip_line_value, amount, 2):
                error.append("Code: %s - Expected Amount: %s - Reality: %s" % (code, amount, payslip_line_value))
        for line in payslip.worked_days_line_ids:
            if line.code not in results:
                error.append("Missing Line: '%s' - %s Days - %s Hours - %s CHF," % (
                    line.code,
                    line_values[line.code][payslip.id]['number_of_days'],
                    line_values[line.code][payslip.id]['number_of_hours'],
                    line_values[line.code][payslip.id]['amount'],
                ))
        if error:
            error.extend([
                f"Payslip Period: {payslip.date_from} - {payslip.date_to}",
                "Payslip Actual Values: ",
                "        {"
            ])
            for line in payslip.worked_days_line_ids:
                error.append("            '%s': (%s, %s, %s)," % (
                    line.code,
                    line_values[line.code][payslip.id]['number_of_days'],
                    line_values[line.code][payslip.id]['number_of_hours'],
                    line_values[line.code][payslip.id]['amount'],
                ))
            error.append("        }")
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def _validate_payslip(self, payslip, results, skip_lines=False):
        error = []
        line_values = payslip._get_line_values(set(results.keys()) | set(payslip.line_ids.mapped('code')))
        for code, value in results.items():
            payslip_line_value = line_values[code][payslip.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Code: %s - Expected: %s - Reality: %s" % (code, value, payslip_line_value))
        if not skip_lines:
            for line in payslip.line_ids:
                if line.code not in results:
                    error.append("Missing Line: '%s' - %s," % (line.code, line_values[line.code][payslip.id]['total']))
        if error:
            error.extend([
                f"Payslip Period: {payslip.date_from} - {payslip.date_to}",
                "Payslip Actual Values: ",
                "        payslip_results = {" + ', '.join(f"'{line.code}': {line_values[line.code][payslip.id]['total']}" for line in payslip.line_ids) + "}"
            ])
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))
