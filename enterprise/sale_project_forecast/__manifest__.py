# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Project Forecast',
    'category': 'Hidden',
    'description': """
This module allows you to schedule your Sales Order based on the product configuration.

For products on which the "Plan Services" option is enabled, you will have the opportunity
to automatically forecast the shifts for employees whom are able to take the shift
(i.e. employees who have the same role as the one configured on the product).

Forecast shifts and keep an eye on the hours consumed on your plannable products.
    """,
    'depends': ['sale_planning', 'sale_project', 'project_forecast'],
    'data': [
        'views/planning_slot_views.xml',
        'views/planning_templates.xml',
        'views/product_template_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
