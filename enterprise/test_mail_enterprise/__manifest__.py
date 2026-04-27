# -*- coding: utf-8 -*-

{
    'name': 'Mail Tests (Enterprise)',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'summary': 'Mail Tests: performances and tests specific to mail with all sub-modules',
    'description': """This module contains tests related to mail. Those are
present in a separate module as it contains models used only to perform
tests independently to functional aspects of other models. Moreover most of
modules build on mail (sms, snailmail, mail_enterprise) are set as dependencies
in order to test the whole mail codebase. """,
    'depends': [
        'documents',
        'mail',
        'mail_bot',
        'mail_enterprise',
        'mass_mailing',
        'mass_mailing_sms',
        'marketing_automation',
        'marketing_automation_sms',
        'mail_mobile',
        'portal',
        'rating',
        'snailmail',
        'sms',
        'test_mail',
        'test_mail_full',
        'test_mass_mailing',
        'test_mail_sms',
        'voip',
        'test_whatsapp',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_unit_tests': [
            'test_mail_enterprise/static/tests/**/*',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
