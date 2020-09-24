# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Odoo Web core module.
========================

This module provides the core of the Odoo Web Client.
        """,
    'depends': ['base'],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/webclient_templates.xml',
        'views/report_templates.xml',
        'views/base_document_layout_views.xml',
        'data/report_layout.xml',
    ],
    'qweb': [
        "static/src/xml/base.xml",
        "static/src/xml/chart.xml",
        "static/src/xml/fields.xml",
        "static/src/xml/file_upload_progress_bar.xml",
        "static/src/xml/file_upload_progress_card.xml",
        "static/src/xml/kanban.xml",
        "static/src/xml/menu.xml",
        "static/src/xml/notification.xml",
        "static/src/xml/pivot.xml",
        "static/src/xml/rainbow_man.xml",
        "static/src/xml/report.xml",
        "static/src/xml/search_panel.xml",
        "static/src/xml/web_calendar.xml",
    ],
    'bootstrap': True,  # load translations for login screen
}
