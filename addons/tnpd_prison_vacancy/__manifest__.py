# Part of TNPD Prison Management System.
# License: LGPL-3

{
    'name': 'TNPD Prison Vacancy Management',
    'version': '19.0.1.0.0',
    'category': 'Prison Management',
    'summary': 'Prison-wise staff vacancy master data and transfer availability API',
    'description': """
Prison Vacancy Management
=========================
Maintains prison-wise staff sanctioned strength, occupied count, and vacancy
figures as master data loaded automatically on installation.

Features
--------
* ``prison.vacancy`` model with one record per prison facility
* Seed data for all Tamil Nadu prison facilities (loaded on install via XML)
* REST API: check vacancy availability for transfer validation
* REST API: bulk import and manual update of vacancy data
* Auth-gated endpoints (requires valid Odoo session)
    """,
    'author': 'TNPD',
    'website': '',
    'license': 'LGPL-3',

    'depends': ['base', 'prison_jail_master'],

    'data': [
        'security/ir.model.access.csv',
        'data/prison_jail_extra.xml',
        'data/prison_vacancy_data.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
