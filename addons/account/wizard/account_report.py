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

class account_report(osv.osv_memory):
    _name = "account.report"
    _inherit = "account.common.report"
    _description = "Account Report"

    _columns = {
        'parent_id': fields.many2one('account.report', 'Report'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of invoice tax."),
        'type': fields.selection([
            ('sum','Sum'),
            ('accounts','Accounts'),
            ('account_report','Account Report'),
            ],'Type'),
        'account_ids': fields.many2many('account.account', 'account_account_report', 'report_line_id', 'account_id', 'Accounts'),
        'note': fields.text('Notes'),
        'account_report_id':  fields.many2one('account.report', 'Account Reports'),
        'enable_comparison': fields.boolean('Enable Comparison'),
    }

account_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
