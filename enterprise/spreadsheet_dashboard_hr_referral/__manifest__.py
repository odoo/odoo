# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for recruitment",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'hr_referral', 'hr_contract_salary'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['hr_referral', 'hr_contract_salary'],
    'license': 'OEEL-1',
}
