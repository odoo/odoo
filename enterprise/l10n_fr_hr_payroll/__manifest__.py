# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'French Payroll',
    'countries': ['fr'],
    'category': 'Human Resources/Payroll',
    'author': 'Yannick Buron (SYNERPGY)',
    'depends': ['hr_payroll'],
    'description': """
French Payroll Rules.
=====================

    - Configuration of hr_payroll for French localization
    - All main contributions rules for French payslip, for 'cadre' and 'non-cadre'
    - New payslip report

This module was not done by the R&D Payroll team. We can't promise you the accuracy of the data it contains.
============================================================================================================

    """,
    'data': [
        'data/l10n_fr_hr_payroll_data.xml',
        'data/l10n_fr_hr_payroll_employe_cadre_data.xml',
        'data/l10n_fr_hr_payroll_employe_non_cadre_data.xml',
        'views/l10n_fr_hr_payroll_view.xml',
        'views/res_config_settings_views.xml',
        'report/report_l10n_fr_fiche_paye.xml',
        'report/l10n_fr_hr_payroll_report.xml',
    ],
    'license': 'OEEL-1',
}
