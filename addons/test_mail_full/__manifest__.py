# -*- coding: utf-8 -*-

{
    'name': 'Mail Tests (Full)',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'summary': 'Mail Tests: performances and tests specific to mail with all sub-modules',
    'description': """This module contains tests related to various mail features
and mail-related sub modules. Those tests are contained in a separate module as it
contains models used only to perform tests independently to functional aspects of
real applications. """,
    'depends': [
        'test_mail',
        'mail',
        'mail_bot',
        # 'snailmail',
        'mass_mailing',
        'mass_mailing_sms',
        'phone_validation',
        'sms',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
}
