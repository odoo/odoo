# -*- coding: utf-8 -*-

# Created on 2017-11-05
# author: 广州尚鹏，http://www.sunpop.cn
# email: 300883@qq.com
# resource of Sunpop
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Odoo在线中文用户手册（长期更新）
# http://www.sunpop.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# http://www.sunpop.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# http://www.sunpop.cn/odoo10_developer_document_offline/
# description:
{
    'name': 'App Odoo Customize(Backend Debranding Title,Language,Documentation,Quick Debug,Delete clear)',
    'version': '10.0.1.0',
    'author': 'Sunpop.cn',
    'category': 'Productivity',
    'website': 'http://www.sunpop.cn',
    'license': 'AGPL-3',
    'sequence': 2,
    'summary': 'Quick customize and debranding your own Odoo. Quick debug, Language Switcher, Online Documentation Access,Delete test data.',
    'description': """

App Odoo Customize(Debranding Title,Language,Documentation,Quick Debug)
============
White label odoo.
You can config odoo, make it look like your own platform.
1. Deletes Odoo label in footer
2. Replaces "Odoo" in Windows title
3. Customize Documentation, Support, About links and title in usermenu
4. Adds "Developer mode" link to the top right-hand User Menu.
5. Adds Quick Language Switcher to the top right-hand User Menu.
6. Adds Country flags  to the top right-hand User Menu.
7. Adds English and Chinese user documentation access to the top right-hand User Menu.
8. Adds developer documentation access to the top right-hand User Menu.
9. Customize "My odoo.com account" button
10. Standalone setting panel, easy to setup.
11. Provide 236 country flags.
12. Multi-language Support.
13. Change Powered by Odoo in login screen.(Please change '../views/app_odoo_customize_view.xml' #15)
14. Quick delete test data in Apps: Sales/POS/Purchase/MRP/Inventory/Accounting/Message/Workflow etc.
15. Reset All the Sequence to beginning of 1: SO/PO/MO/Invoice...

This module can help to white label the Odoo.
Also helpful for training and support for your odoo end-user.
The user can get the help document just by one click.

    """,
    'images': ['static/description/banner.png'],
    'depends': ['web'],
    'data': [
        'views/app_odoo_customize_view.xml',
        'views/app_theme_config_settings_view.xml',
        # data
        'data/ir_config_parameter.xml',
    ],
    'demo': [],
    'test': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [
        'static/src/xml/customize_user_menu.xml',
    ],
}

