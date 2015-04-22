# -*- encoding: utf-8 -*-

{
    'name': 'Lunch',
    'author': 'OpenERP SA',
    'version': '0.2',
    'depends': ['base', 'report'],
    'category': 'Tools',
    'summary': 'Lunch Order, Meal, Food',
    'description': """
The base module to manage lunch.
================================

Many companies order sandwiches, pizzas and other, from usual suppliers, for their employees to offer them more facilities. 

However lunches management within the company requires proper administration especially when the number of employees or suppliers is important. 

The “Lunch Order” module has been developed to make this management easier but also to offer employees more tools and usability. 

In addition to a full meal and supplier management, this module offers the possibility to display warning and provides quick order selection based on employee’s preferences.

If you want to save your employees' time and avoid them to always have coins in their pockets, this module is essential.
    """,
    'data': [
        'security/lunch_security.xml',
        'views/lunch_views.xml',
        'views/lunch_templates.xml',
        'wizard/lunch_order_view.xml',
        'wizard/lunch_validation_view.xml',
        'wizard/lunch_cancel_view.xml',
        'report/lunch_report_views.xml',
        'report/report_lunch_order_view.xml',
        'report/lunch_order_templates.xml',
        'security/ir.model.access.csv',
    ],
    'demo': ['data/lunch_demo.xml'],
    'installable': True,
    'application': True,
    'certificate': '001292377792581874189',
}
