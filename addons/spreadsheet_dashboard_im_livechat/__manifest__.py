# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for live chat",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'im_livechat'],
    'data': [
        "data/livechat_ongoing_sessions_actions.xml",
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['im_livechat'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
