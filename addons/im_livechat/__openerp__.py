{
    'name' : 'Live Support',
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
        "im_livechat_view.xml",
    ],
    'demo': [
        "im_livechat_demo.xml",
    ],
    'depends' : ["im", "mail"],
    'installable': True,
    'auto_install': False,
    'application': True,
}
