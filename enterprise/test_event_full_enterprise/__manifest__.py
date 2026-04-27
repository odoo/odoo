{
    'name': 'Event Test (all modules)',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """
This module will test the main event flows of Odoo, both frontend and backend.
It installs sale capabilities, front-end flow, eCommerce, questions and
automatic lead generation, full Online support, sms and whatsapp support, ...
""",
    'depends': [
        'event_social',
        'test_event_full',
        'whatsapp_event',
    ],
    'license': 'LGPL-3',
}
