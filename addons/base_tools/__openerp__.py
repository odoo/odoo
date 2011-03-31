# -*- encoding: utf-8 -*-
{
    "name": "Base Tools",
    "author": "OpenERP SA",
    "version": "1.0",
    "depends": ["base"],
    "category" : "Tools",
    'description': """
Common base for tools modules.
==============================

Creates menu link for Tools from where tools like survey, lunch, idea, etc. are accessible if installed.
    """,
    "init_xml": [],
    "update_xml": [
        'tools_view.xml'
    ],
    "installable": True,
    "certificate" : "00571588675379342237"
}
