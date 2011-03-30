# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    "name": "Project MailGateWay",
    "version": "1.1",
    "author": "OpenERP SA",
    "website": "http://www.openerp.com",
    "category": "Project Management",
    "images": ["images/project_mailgate_task.jpeg"],
    "depends": ["project", "email"],
    "description": """
This module is an interface that synchronises mails with OpenERP Project Task.
==============================================================================

It allows creating tasks as soon as a new mail arrives in our configured mail server.
Moreover, it keeps track of all further communications and task states.
    """,
    "init_xml": [],
    "update_xml": ["security/ir.model.access.csv",
        "project_mailgate_view.xml",
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
    'certificate': '001075048780413258261',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
