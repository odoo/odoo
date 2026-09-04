# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Junaidul Ansar M (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    'name': 'Reset Journal Entries',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Using this module, multiple journal entries can be set as '
               'draft, canceled, and reposted in invoicing.',
    'description': 'This module is used to change multiple journal entries to '
                   'the draft stage. By doing This we can review and verify '
                   'again in the journal. Sometimes when creating the Journal '
                   'entries may not have all the necessary information or '
                   'details at hand; sometimes they need to go through an '
                   'approval process before they can be posted. In certain '
                   'cases, you may need to record a transaction temporarily for'
                   ' record-keeping purposes but do not want it to affect your'
                   ' financial statements until later. When you are in the '
                   'process of preparing multiple journal entries related to a '
                   'specific event or project, you might want to keep them in '
                   '"Draft" status until all entries are ready for posting to'
                   ' maintain consistency. In all these cases, we can use this '
                   'module',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['account'],
    'data': [
        'data/ir_action_server_data.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
