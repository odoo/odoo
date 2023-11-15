# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Contract based Attendances',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
    Compute overtime and expected attendances based on contract history
    """,
    'depends': ['hr_attendance', 'hr_contract'],
    'installable': True,
    'license': 'LGPL-3',
}
