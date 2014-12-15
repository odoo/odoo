# -*- coding: utf-8 -*-
{
    'name': "Website Portal",
    'summary': "Website Portal",
    'description': "Display portal in website",
    'author': 'OpenERP SA',
    'category': 'Website',
    'version': '1.0',
    'depends': ["base", "portal", "website", "web"],
    'data': ["views/website_portal.xml", "data/website_portal_data.xml"],
    'auto_install': False,
}
