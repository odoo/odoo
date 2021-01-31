# -*- coding: utf-8 -*-
##############################################################################
{
    "name": "Workflow Customization Powerfully 13.0,强大的自定义工作流解决方案",
    "version": "12",
    'license': 'OPL-1',
    "website": "http://47.104.249.25",
    "depends": ["base","web", "purchase", "calendar"],
    "author": "<Jon alangwansui@qq.com>",
    "category": "Tools",
    "description": """
       An Powerfully Custom Workflow Tool.
    """,
    "data": [
        'secureity/ir.model.access.csv',
        'views/wkf.xml',
        'wizard/wizard_wkf.xml',
    ],

    'demo':[
        'demo/wkf.base.csv',
        'demo/wkf.node.csv',
        'demo/wkf.trans.csv',
    ],
    #'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'application':True,
    'active': True,
    'price': 150,
    'currency': 'EUR',
    'auto_install': True,
    'images': [
        'static/description/theme.jpg',
    ],

}
