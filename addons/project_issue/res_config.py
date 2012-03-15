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

from osv import fields, osv

class project_issue_mail_configuration(osv.osv_memory):
    _inherit = 'project.config.settings'
    _columns = {
        'project_claim': fields.boolean("Create claims from an email account",
                        help="""Allows you to configure your incoming mail server. And creates claims for your mails.
                        """),
        'claim_server' : fields.char('Server Name', size=256),
        'claim_port' : fields.integer('Port'),
        'claim_type': fields.selection([
                   ('pop', 'POP Server'),
                   ('imap', 'IMAP Server'),
                   ('local', 'Local Server'),
               ], 'Server Type'),
        'claim_is_ssl': fields.boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP=995)"),
        'claim_user' : fields.char('Username', size=256),
        'claim_password' : fields.char('Password', size=1024),
    }
    _defaults = {
        'claim_type': 'pop',
    }

    def get_default_issue_server(self, cr, uid, ids, context=None):
        context = {'type':'claim'}
        res = self.get_default_email_configurations(cr, uid, ids, context)
        return res

    def set_default_issue_server(self, cr, uid, ids, context=None):
        context = {'type':'issue','obj':'project.issue'}
        res = self.set_email_configurations(cr, uid, ids, context)


project_issue_mail_configuration()