# -*- coding: utf-8 -*-

# Created on 2018-11-26
# author: 广州尚鹏，https://www.sunpop.cn
# email: 300883@qq.com
# resource of Sunpop
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Odoo12在线用户手册（长期更新）
# https://www.sunpop.cn/documentation/user/12.0/en/index.html

# Odoo12在线开发者手册（长期更新）
# https://www.sunpop.cn/documentation/12.0/index.html

# Odoo10在线中文用户手册（长期更新）
# https://www.sunpop.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# https://www.sunpop.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# https://www.sunpop.cn/odoo10_developer_document_offline/
# description:

{
    'name': 'odoo Customize OEM(Boost, Data reset)',
    'version': '14.20.11.06',
    'author': 'Sunpop.cn',
    'category': 'Productivity',
    'website': 'https://www.sunpop.cn',
    'license': 'LGPL-3',
    'sequence': 2,
    'summary': """
    1 click customize odoo, reset data. For quick develop. Set brand, boost, reset data, debug. Language Switcher. 
    Easy Delete data.reset account chart.
    customize my odoo. odoo customize, odoo oem.
    """,
    'description': """
    
    App Customize Odoo (Change Title,Language,Documentation,Quick Debug)
    ============
    White label odoo.
    Support Odoo 14, 13, 12, 11, 10, 9.
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
    14. Quick delete test data in Apps: Sales/POS/Purchase/MRP/Inventory/Accounting/Project/Message/Workflow etc.
    15. Reset All the Sequence to beginning of 1: SO/PO/MO/Invoice...
    16. Fix odoo reload module translation bug while enable english language
    17. Stop Odoo Auto Subscribe(Moved to app_odoo_boost)
    18. Show/Hide Author and Website in Apps Dashboard
    19. One Click to clear all data (Sometime pls click twice)
    20. Show quick upgrade in app dashboard, click to show module info not go to odoo.com
    21. Can clear and reset account chart. Be cautious
    22. Update online manual and developer document to odoo12
    23. Add reset or clear website blog data
    24. Customize Odoo Native Module(eg. Enterprise) Url
    25. Add remove expense data
    26. Add multi uninstall modules
    27. Add odoo boost modules link.
    28. Easy Menu manager.
    29. Apps version compare. Add Install version in App list. Add Local updatable filter in app list.
    30. 1 key export app translate file like .po file.
    31. Show or hide odoo Referral in the top menu.
    32. Fix odoo bug of complete name bug of product category and stock location..
    33. Add Demo Ribbon Setting.
    34. Add Remove all quality data.
    35. Fixed for odoo 14.
    36. Add refresh translate for multi module.
    
    This module can help to white label the Odoo.
    Also helpful for training and support for your odoo end-user.
    The user can get the help document just by one click.
    ## 在符合odoo开源协议的前提下，去除odoo版权信息，自定义你的odoo
    可完全自行设置下列 odoo 选项，让 odoo 看上去像是你的软件产品
    支持Odoo 14,13,12, 11, 10, 9 版本，社区版企业版通用    
    1. 删除菜单导航页脚的 Odoo 标签
    2. 将弹出窗口中 "Odoo" 设置为自定义名称
    3. 自定义用户菜单中的 Documentation, Support, About 的链接
    4. 在用户菜单中增加快速切换开发模式
    5. 在用户菜单中增加快速切换多国语言
    6. 对语言菜单进行美化，设置国旗图标
    7. 在用户菜单中增加中/英文用户手册，可以不用翻墙加速了
    8. 在用户菜单中增加开发者手册，含python教程，jquery参考，Jinja2模板，PostgresSQL参考
    9. 在用户菜单中自定义"My odoo.com account"
    10. 单独设置面板，每个选项都可以自定义
    11. 提供236个国家的国旗文件（部份需要自行设置文件名）
    12. 多语言版本
    13. 自定义登陆界面中的 Powered by Odoo
    14. 快速删除测试数据，支持模块包括：销售/POS门店/采购/生产/库存/会计/项目/消息与工作流等.
    15. 将各类单据的序号重置，从1开始，包括：SO/PO/MO/Invoice 等
    16. 修复odoo启用英文后模块不显示中文的Bug
    17. 可停用odoo自动订阅功能，避免“同样对象关注2次”bug，同时提升性能
    18. 显示/隐藏应用的作者和网站-在应用安装面板中
    19. 一键清除所有数据（视当前数据情况，有时需点击2次）
    20. 在应用面板显示快速升级按键，点击时不会导航至 odoo.com
    21. 清除并重置会计科目表
    22. 全新升级将odoo12用户及开发手册导航至国内网站，或者自己定义的网站
    23. 增加清除网站数据功能
    24. 自定义 odoo 原生模块跳转的url(比如企业版模块)
    25. 增加删除费用报销数据功能
    26. 增加批量卸载模块功能
    27. 增加odoo加速功能
    28. 快速管理顶级菜单
    29. App版本比较，快速查看可本地更新的模块
    30. 一键导出翻译文件 po
    31. 显示或去除 odoo 推荐
    32. 增加修复品类及区位名的操作 
    33. 增加 Demo 的显示设置 
    34. 增加清除质检数据 
    35. 优化至odoo14适用 
    36. 可为多个模块强制更新翻译 
    """,
    'images': ['static/description/banner.gif'],
    'depends': [
        'base_setup',
        'web',
        'mail',
        'iap',
        # 'digest',
        # when enterprise
        # 'web_mobile'
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/app_odoo_customize_views.xml',
        'views/app_theme_config_settings_views.xml',
        'views/res_config_settings_views.xml',
        'views/ir_views.xml',
        'views/ir_module_module_views.xml',
        'views/ir_translation_views.xml',
        'views/ir_ui_menu_views.xml',
        'views/ir_ui_view_views.xml',
        'views/ir_model_fields_views.xml',
        # data
        'data/ir_config_parameter_data.xml',
        'data/ir_module_module_data.xml',
        # 'data/digest_template_data.xml',
        'data/res_company_data.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'demo': [],
    'test': [],
    'css': [],
    'js': [],
    # 'pre_init_hook': 'pre_init_hook',
    # 'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': True,
}
