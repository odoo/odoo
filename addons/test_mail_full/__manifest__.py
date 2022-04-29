# -*- coding: utf-8 -*-

{
    'name': 'Mail Tests (Full)',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'summary': 'Mail Tests: performances and tests specific to mail with all sub-modules',
    'description': """This module contains tests related to various mail features
and mail-related sub modules. Those tests are present in a separate module as it
contains models used only to perform tests independently to functional aspects of
real applications. """,
    'depends': [
        'test_mail',
        'test_mass_mailing',
        'mail',
        'mail_bot',
        'portal',
        'rating',
        # 'snailmail',
        'mass_mailing',
        'mass_mailing_sms',
        'phone_validation',
        'sms',
    ],
    'data': [
        'data/mail_message_subtype_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
