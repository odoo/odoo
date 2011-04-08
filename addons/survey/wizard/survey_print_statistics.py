# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
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

from osv import osv
from osv import fields
from tools.translate import _

class survey_print_statistics(osv.osv_memory):
    _name = 'survey.print.statistics'
    _columns = {
        'survey_ids': fields.many2many('survey','survey_print_statistics','survey_id',\
                                'print_id', "Survey", required="1"),
    }

    def action_next(self, cr, uid, ids, context=None):
        """
        Print Survey Statistics in pdf format.

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey statistics IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value for created survey statistics report
        """
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, ['survey_ids'], context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'survey.print.statistics'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'survey.analysis',
            'datas': datas,
        }

survey_print_statistics()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
