{
    'name': 'POS No Followup',
    'summary': 'POS "no followup" handeling.',
    'description': '''During the rework of the follow-up report in 18.0, the
    "No Follow-Up" field from journal items was removed, making it impossible to exclude
    individual journal items from triggering a follow-up. This was added back in 19.0.
    This module ports the feature back in 18.0 for point of sale.''',
    'category': 'Hidden',
    'depends': ['pos_enterprise', 'account_no_followup'],
    'auto_install': True,
    'license': 'LGPL-3',
}
