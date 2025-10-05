# -*- coding: utf-8 -*-

# Created on 2023-02-02
# author: 欧度智能，https://www.odooai.cn
# email: 300883@qq.com
# resource of odooai
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

# Odoo16在线用户手册（长期更新）
# https://www.odooai.cn/documentation/16.0/zh_CN/index.html

# Odoo16在线开发者手册（长期更新）
# https://www.odooai.cn/documentation/16.0/zh_CN/developer.html

# Odoo13在线用户手册（长期更新）
# https://www.odooai.cn/documentation/user/13.0/zh_CN/index.html

# Odoo13在线开发者手册（长期更新）
# https://www.odooai.cn/documentation/13.0/index.html

# Odoo10在线中文用户手册（长期更新）
# https://www.odooai.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# https://www.odooai.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# https://www.odooai.cn/odoo10_developer_document_offline/

##############################################################################
#    Copyright (C) 2009-TODAY odooai.cn Ltd. https://www.odooai.cn
#    Author: Ivan Deng，300883@qq.com
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#    See <http://www.gnu.org/licenses/>.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##############################################################################

{
    'name': "odooAi Common Util and Tools,欧度智能基础功能及面板",
    'version': '19.0.25.09.25',
    'author': 'odooai.cn',
    'category': 'Extra tools',
    'website': 'https://www.odooai.cn',
    'live_test_url': 'https://demo.odooapp.cn',
    'license': 'LGPL-3',
    'sequence': 2,
    'price': 0.00,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'summary': '''
    Core for common use for odooai.cn apps.
    基础核心及云面板，必须没有要被依赖字段及视图等，实现auto_install
    ''',
    'description': '''
    need to setup odoo.conf, add follow:
    server_wide_modules = web,app_common
    1. Quick import data from excel with .py code
    2. Quick m2o default value
    3. Filter for useless field
    4. UTC local timezone convert
    5. Get browser ua, user-agent
    6. Image to local, image url to local, media to local attachment
    7. Log cron job
    8. Boost for less no use mail
    9. Customize .rng file
    10. Misc like get distance between two points
    11. Multi-language Support. Multi-Company Support.
    12. Support Odoo 18,17,16,15,14,13,12, Enterprise and Community and odoo.sh Edition.
    13. Full Open Source.
    ==========
    1.
    2.
    3. 多语言支持
    4. 多公司支持
    5. Odoo 16, 企业版，社区版，多版本支持
    ''',
    'depends': [
        'mail',
        'base_setup',
        'web',
    ],
    'data': [
        'data/ir_module_category_data.xml',
        'data/res_groups_privilege_data.xml',
        'wizard/mail_compose_message_views.xml',
        'views/res_config_settings_views.xml',
        'views/ir_cron_views.xml',
        # 'report/.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'demo': [],
    # 'pre_init_hook': 'pre_init_hook',
    # 'post_init_hook': 'post_init_hook',
    # 'uninstall_hook': 'uninstall_hook',
    # 可以不需要，因为直接放 common中了
    # 'external_dependencies': {'python': ['pyyaml', 'ua-parser', 'user-agents']},
    'installable': True,
    'application': True,
    'auto_install': True,
}
