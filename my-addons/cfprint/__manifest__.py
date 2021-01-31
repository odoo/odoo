# -*- coding: utf-8 -*-
# 康虎软件工作室
# http://www.khcloud.net
# QQ: 360026606
# wechat: 360026606
#--------------------------

{
    'name': "cfprint",

    'summary': """
        康虎云报表基础模块，基于康虎云报表的打印功能必须依赖此模块。
        """,

    'description': """
康虎云报表基础模块
============================
基于康虎云报表的打印功能必须依赖此模块。


本模块主要功能：
----------------------------
* 引入康虎云报表所需的javascript库
* 实现打印模板管理功能，模板可以存入数据库，便于统一管理（从菜单  设置--技术--报告--康虎云报表 进入）
* 增加了根据原QWeb报表取值功能，该功能按QWeb模板中的方式取值，但把HTML去掉，否则数据不干净
* (功能持续增加中...)

    """,

    'author': "康虎软件工作室（QQ：360026606， 微信：360026606）",
    'website': "http://www.khcloud.net",
    'category': 'CFSoft',
    'version': '14.0.6.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail'],
    #这里依赖 mail 模块请参考：http://www.khcloud.net:4082/?thread-463.htm

    # always loaded
    'data': [
        'security/ir.model.access.xml',
        'security/security.xml',
        'report/layout_templates.xml',
        'views/cf_template_view.xml',
        'views/cfprint_views.xml',
        'data/template_category_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
