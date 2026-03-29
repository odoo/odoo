# -*- coding: utf-8 -*-

# Created on 2018-11-26
# author: 欧度智能，https://www.odooai.cn
# email: 300883@qq.com
# resource of odooai
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Odoo12在线用户手册（长期更新）
# https://www.odooai.cn/documentation/user/12.0/en/index.html

# Odoo12在线开发者手册（长期更新）
# https://www.odooai.cn/documentation/12.0/index.html

# Odoo10在线中文用户手册（长期更新）
# https://www.odooai.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# https://www.odooai.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# https://www.odooai.cn/odoo10_developer_document_offline/
# description:

{
    'name': 'Kodoo Platform Customization',
    'version': '19.0.26.02.02',
    'author': 'Kodoo',
    'category': 'Extra Tools',
    'website': 'https://kodoo.online',
    'live_test_url': 'https://kodoo.online',
    'license': 'LGPL-3',
    'sequence': 2,
    'images': ['static/description/banner.gif', 'static/description/banner.png'],
    'summary': """
    White-label, admin UX and operational customization tools for the Kodoo platform.
    """,
    'depends': [
        'app_common',
        'base_setup',
        'base_import',
        'base_import_module',
        'portal',
        'mail',
        # 'digest',
        # when enterprise
        # 'web_mobile'
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/app_odoo_customize_views.xml',
        'views/res_config_settings_views.xml',
        'views/ir_views.xml',
        'views/ir_actions_actions_views.xml',
        'views/ir_actions_act_window_views.xml',
        'views/ir_actions_server_views.xml',
        'views/ir_module_addons_path_views.xml',
        'views/ir_module_module_views.xml',
        'views/ir_module_category_views.xml',
        'views/ir_sequence_views.xml',
        'views/ir_ui_menu_views.xml',
        'views/ir_ui_view_views.xml',
        'views/ir_model_data_views.xml',
        'views/ir_model_fields_views.xml',
        'views/ir_model_views.xml',
        # data
        'data/ir_config_parameter_data.xml',
        'data/ir_module_module_data.xml',
        # 'data/digest_template_data.xml',
        # 'data/res_company_data.xml',
        'data/res_config_settings_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'app_odoo_customize/static/src/scss/app.scss',
            'app_odoo_customize/static/src/scss/ribbon.scss',
            'app_odoo_customize/static/src/scss/dialog.scss',
            'app_odoo_customize/static/src/js/user_menu.js',
            'app_odoo_customize/static/src/js/ribbon.js',
            'app_odoo_customize/static/src/js/dialog.js',
            'app_odoo_customize/static/src/js/navbar.js',
            'app_odoo_customize/static/src/js/base_import_list_renderer.js',
            'app_odoo_customize/static/src/js/base_import_list_renderer.js',
            'app_odoo_customize/static/src/webclient/*.js',
            'app_odoo_customize/static/src/webclient/user_menu.xml',
            'app_odoo_customize/static/src/xml/res_config_edition.xml',
            'app_odoo_customize/static/src/xml/base_import.xml',
            'app_odoo_customize/static/src/xml/debug_templates.xml',
        ],
    },
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': True,
    'description': """
    Kodoo platform customization layer for Odoo.

    This module centralizes white-label settings, admin UX improvements,
    user-menu options, branding cleanup and operational utilities used by
    the Kodoo deployment.

    Main capabilities:
    1. Platform title and brand customization
    2. Login and footer branding cleanup
    3. Quick language and debug access
    4. User-menu support, documentation and portal links
    5. Interface and ribbon configuration
    6. Module management helpers and upgrade shortcuts
    7. Safe data cleanup utilities for administrative use
    8. Extra visibility for technical metadata and menus
    ## 在符合odoo开源协议的前提下，自定义你的odoo系统
    可完全自行设置下列选项，将 odoo 整合进自有软件产品
    支持Odoo 19,18,17,16,15,14,13,12,11,10,9 版本，社区版企业版通用
    ============
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
    11. 提供236个国家/地区的国旗文件（部份需要自行设置文件名）
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
    37. noupdate字段的快速管理，主要针对 xml_id
    38. 对话框可拖拽，可缩放，自动大屏优化
    39. 只有系统管理员可以操作快速debug
    40. 增强对企业版的支持
    41. 修正odoo原生移动端菜单bug，点击个人设置时，原菜单不隐藏等
    42. 可设置导航栏在上方还是下方，分开桌面与移动端.
    43. 可设置只允许管理员进入开发者模式，不可在url中直接debut=1来调试
    44. 可配置停用自动用户订阅功能，这会提速odoo，减少资源消耗
    45. 为应用模块增加模块路径信息
    46. 增加快速帮助文档，可以在任意操作中获取相关的 odoo 帮助.
    47. 增加Ai模块相关信息，可以快速访问ai模块，使用ai员工.
    48. 增加可配置的系统调试标签，用于系统测试期提示.
    49. 增加 SaaS 客户端开头，可让用户安装在线翻译同步模块及在线更新(仅odoo18).
    50. 快速菜单管理，快速禁用/启用菜单.
    51. 在开发者Assets模式中，快速查看菜单Menu 的 xml_id.
    52. 快速管理查看模型的字段和视图列表.
    53. 快速管理查看应用权限分类管理.
    """,
}
