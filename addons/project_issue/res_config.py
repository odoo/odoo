# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from osv import osv, fields

class project_issue_settings(osv.osv_memory):
    _name = 'project.config.settings'
    _inherit = ['project.config.settings', 'fetchmail.config.settings']

    _columns = {
        'fetchmail_issue': fields.boolean("Create issues from an email account",
            fetchmail_model='project.issue', fetchmail_name='Incoming issues',
            help="""Allows you to configure your incoming mail server, and create issues from incoming emails."""),
        'issue_server' : fields.char('Server', size=256),
        'issue_port' : fields.integer('Port'),
        'issue_type': fields.selection([
                ('pop', 'POP Server'),
                ('imap', 'IMAP Server'),
                ('local', 'Local Server'),
            ], 'Type'),
        'issue_is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'issue_user' : fields.char('Username', size=256),
        'issue_password' : fields.char('Password', size=1024),
    }

    _defaults = {
        'issue_type': 'pop',
    }
