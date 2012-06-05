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
    "name": "Tasks-Mail Integration",
    "version": "1.1",
    "author": "OpenERP SA",
    "website": "http://www.openerp.com",
    "category": "Project Management",
    "images": ["images/project_mailgate_task.jpeg"],
    "depends": ["project", "mail"],
    "description": """
This module can automatically create Project Tasks based on incoming emails
===========================================================================

Allows creating tasks based on new emails arriving at a given mailbox,
similarly to what the CRM application has for Leads/Opportunities.
There are two common alternatives to configure the mailbox integration:

 * Install the ``fetchmail`` module and configure a new mailbox, then select
   ``Project Tasks`` as the target for incoming emails.
 * Set it up manually on your mail server based on the 'mail gateway' script
   provided in the ``mail`` module - and connect it to the `project.task` model.


    """,
    "init_xml": [],
    "update_xml": ["security/ir.model.access.csv",
    ],
    'demo_xml': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '001075048780413258261',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
