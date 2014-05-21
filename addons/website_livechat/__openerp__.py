{
    'name': 'LiveChat',
    'category': 'Website',
    'summary': 'Chat With Your Website Visitors',
    'version': '1.0',
    'description': """
OpenERP Website LiveChat
========================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'im_livechat'],
    'installable': True,
    'data': [
        'views/website_livechat.xml',
        'views/res_config.xml'
    ],
}
