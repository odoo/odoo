{
    'name' : 'Live Support',
    'author': 'OpenERP SA',
    'version': '1.0',
    'summary': 'Live Chat with Visitors/Customers',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
Live Chat Support
=================

Allow to drop instant messaging widgets on any web page that will communicate
with the current server and dispatch visitors request amongst several live
chat operators.

        """,
    'data': [
        "security/im_livechat_security.xml",
        "security/ir.model.access.csv",
        "views/im_livechat_view.xml",
        "views/im_livechat.xml"
    ],
    'demo': [
        "im_livechat_demo.xml",
    ],
    'depends' : ["mail", "im_chat"],
    'installable': True,
    'auto_install': False,
    'application': True,
}
