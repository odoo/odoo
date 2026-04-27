{
    'name': 'Account No Followup',
    'summary': 'Add "no followup" field to journal items.',
    'description': '''During the rework of the follow-up report in 18.0, the
    "No Follow-Up" field from journal items was removed, making it impossible to exclude
    individual journal items from triggering a follow-up. This was added back in 19.0.
    This module ports the feature back in 18.0''',
    'category': 'Accounting/Accounting',
    'depends': ['account_followup'],
    'data': [
        'views/account_move_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'account_no_followup/static/src/components/**/*',
        ],
    },
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': "uninstall_hook",
}
