#  Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Timesheet direct link",
    'version': '1.0',
    'summary': "Link MRP to Timesheet",
    'category': 'Manufacturing/Manufacturing',
    'depends': ['project_mrp', 'hr_timesheet'],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
