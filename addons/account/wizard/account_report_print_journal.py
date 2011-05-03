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

from osv import osv, fields

class account_print_journal(osv.osv_memory):
    _inherit = "account.common.journal.report"
    _name = 'account.print.journal'
    _description = 'Account Print Journal'

    _columns = {
        'sort_selection': fields.selection([('date', 'Date'),
                                            ('ref', 'Reference Number'),],
                                            'Entries Sorted by', required=True),
    }
    _defaults = {
        'sort_selection': 'date',
    }

    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['sort_selection'], context=context)[0])
        return {'type': 'ir.actions.report.xml', 'report_name': 'account.journal.period.print', 'datas': data}

account_print_journal()

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: