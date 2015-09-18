# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'French Payroll',
    'category': 'Localization/Payroll',
    'author': 'Yannick Buron (SYNERPGY)',
    'depends': ['hr_payroll', 'l10n_fr'],
    'version': '1.0',
    'description': """
French Payroll Rules.
=====================

    - Configuration of hr_payroll for French localization
    - All main contributions rules for French payslip, for 'cadre' and 'non-cadre'
    - New payslip report

TODO:
-----
    - Integration with holidays module for deduction and allowance
    - Integration with hr_payroll_account for the automatic account_move_line
      creation from the payslip
    - Continue to integrate the contribution. Only the main contribution are
      currently implemented
    - Remake the report under webkit
    - The payslip.line with appears_in_payslip = False should appears in the
      payslip interface, but not in the payslip report
    """,

    'active': False,
    'data': [
        'l10n_fr_hr_payroll_view.xml',
        'l10n_fr_hr_payroll_data.xml',
        'views/report_l10nfrfichepaye.xml',
        'l10n_fr_hr_payroll_reports.xml',
    ],
    'installable': True
}
