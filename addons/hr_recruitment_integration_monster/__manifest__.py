# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Integration Monster',
    'version': '1.0',
    'category': 'Human Resources/Recruitment/Integration',
    'description': """
module for monster integration.
========================================
This module provides a base for the integration of recruitment with external
api from Monster.
    """,
    'depends': [
        'hr_recruitment',
        'hr_recruitment_integration_base',
    ],
    'data': [
    ],
    'license': 'LGPL-3',
}
