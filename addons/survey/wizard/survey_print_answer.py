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

class survey_print_answer(osv.osv_memory):
    _name = 'survey.print.answer'
    _columns = {
        'response_ids': fields.many2many('survey.response','survey_print_response',\
                            'response_id','print_id', "Answer", required="1"),
        'orientation': fields.selection([('vertical','Portrait(Vertical)'),\
                            ('horizontal','Landscape(Horizontal)')], 'Orientation'),
        'paper_size': fields.selection([('letter','Letter (8.5" x 11")'),\
                            ('legal','Legal (8.5" x 14")'),\
                            ('a4','A4 (210mm x 297mm)')], 'Paper Size'),
        'page_number': fields.boolean('Include Page Number'),
        'without_pagebreak': fields.boolean('Print Without Page Breaks')
    }

    _defaults = {
        'orientation': lambda *a:'vertical',
        'paper_size': lambda *a:'letter',
        'page_number': lambda *a: 0,
        'without_pagebreak': lambda *a: 0
    }

    def action_next(self, cr, uid, ids, context=None):
        """
        Print Survey Answer in pdf format.

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of print answer IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for created survey answer report
        """
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, ['response_ids', 'orientation', 'paper_size',\
                             'page_number', 'without_pagebreak'], context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'survey.print.answer'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'survey.browse.response',
            'datas': datas,
        }

survey_print_answer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
