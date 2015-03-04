# -*- coding: utf-8 -*-
{
    'name': "SEPA Credit Transfer",
    'summary': """Export payments as SEPA Credit Transfer files""",
    'description': """
        Generate payment orders as pain.001.001.03 messages. The generated XML file can then be uploaded to your bank.

        In order to use the functionality, you must enable SEPA payments on the relevants bank journals.

        The generated files follow the implementation guidelines issued by the European Payment Council and are compatible with formats pain.001.001.04 and pain.001.001.05
        For more informations about the SEPA standards : http://www.iso20022.org/
    """,
    'author': "Odoo SA",
    'category': 'Accounting &amp; Finance',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'views/account_views_additions.xml',
        'views/account_sepa_credit_transfer_view.xml',
        'templates/pain_001_001_03.xml',
        'data/account_sepa.xml'
    ],
}
