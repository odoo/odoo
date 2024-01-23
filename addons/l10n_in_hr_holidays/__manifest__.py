# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'India - Time Off',
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'countries': ['in'],
    'summary': 'Management of leaves for Emplyees in India',
    'depends': ['hr_holidays', 'l10n_in_hr_payroll'],
    'auto_install': True,
    'license': 'LGPL-3',
    'post_init_hook':'_generate_public_leaves',
}
