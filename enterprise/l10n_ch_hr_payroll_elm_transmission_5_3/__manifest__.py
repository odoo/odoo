# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Swissdec Certified Payroll ELM 5.3',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ch'],
    'category': 'Human Resources/Payroll',
    'depends': ['l10n_ch_hr_payroll_elm_transmission'],
    'auto_install': ['l10n_ch_hr_payroll_elm_transmission'],
    'version': '1.0',
    'description': """
This module extends the certification to ELM 5.1 and ELM 5.3 adds various quality of life improvements, such as: 
- Possibility to attribute LPP amounts in %
- Add custom amounts for employer parts for LAAC and IJM
    """,
    'data': [
        'data/hr_salary_rule_data.xml',
        'security/ir.model.access.csv',
        'views/l10n_ch_contract_wage_type_views.xml',
        'views/l10n_ch_laac_views.xml',
        'views/l10n_ch_ijm_views.xml',
        'views/l10n_ch_caf_views.xml',
        'views/l10n_ch_hr_contract_views.xml',
        'views/l10n_ch_lpp_views.xml',
        'views/l10n_ch_hr_employee_views.xml',
        'views/l10n_ch_children_views.xml',
    ],
    'license': 'OEEL-1',
}
