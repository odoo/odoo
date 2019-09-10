{
    'name': 'Campaign in Mass Mailing',
    'version': '1.0',
    'summary': 'This module allow to specify a campaign, a source and a channel for a mass mailing campaign.',
    'author': 'OpenERP SA',
    'description': """
Mass Mailing with Crm Marketing
================================

Link module mass mailing with the marketing mixin from crm.
        """,
    'depends': ['crm', 'mass_mailing'],
    'data': [
        'mass_mailing.xml',
    ],
    'installable': True,
    'auto_install': True,
}
