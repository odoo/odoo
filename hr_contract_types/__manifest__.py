# -*- coding: utf-8 -*-

{
    'name': 'Odoo16 Employee Contracts Types',
    'version': '16.0.1.1.0',
    'category': 'Generic Modules/Human Resources',
    'summary': """
        Contract type in contracts
    """,
    'description': """Odoo16 Employee Contracts Types,Odoo16 Employee, Employee Contracts, Odoo 16""",
    'author': 'Odoo SA,Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['hr', 'hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'views/contract_view.xml',
        'data/hr_contract_type_data.xml',
    ],
    'installable': True,
    'images': ['static/description/banner.png'],
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}