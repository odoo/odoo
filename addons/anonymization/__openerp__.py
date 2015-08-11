# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Database Anonymization',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module allows you to anonymize a database.
===============================================

This module allows you to keep your data confidential for a given database.
This process is useful, if you want to use the migration process and protect
your own or your customer’s confidential data. The principle is that you run
an anonymization tool which will hide your confidential data(they are replaced
by ‘XXX’ characters). Then you can send the anonymized database to the migration
team. Once you get back your migrated database, you restore it and reverse the
anonymization process to recover your previous data.
    """,
    'depends': ['base'],
    'demo': ['anonymization_demo.xml'],
    'data': [
        'ir.model.fields.anonymization.csv',
        'security/ir.model.access.csv',
        'anonymization_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
