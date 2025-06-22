{
    'name': 'HR - Livechat',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Bridge between HR and Livechat.""",
    'depends': ['hr', 'im_livechat'],
    'data': [
        'views/discuss_channel_views.xml',
        'views/im_livechat_channel_member_history_views.xml',
        'views/im_livechat_report_channel_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
