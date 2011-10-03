
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

class survey_print(osv.osv_memory):
    _name = 'survey.print'
    _columns = {
        'survey_ids': fields.many2many('survey', string="Survey", required="1"),
        'orientation' : fields.selection([('vertical','Portrait(Vertical)'),\
                            ('horizontal','Landscape(Horizontal)')], 'Orientation'),
        'paper_size' : fields.selection([('letter','Letter (8.5" x 11")'),\
                            ('legal','Legal (8.5" x 14")'),('a4','A4 (210mm x 297mm)')], 'Paper Size'),
        'page_number' : fields.boolean('Include Page Number'),
        'without_pagebreak' : fields.boolean('Print Without Page Breaks'),
    }

    _defaults = {
        'orientation': lambda *a:'vertical',
        'paper_size': lambda *a:'letter',
        'page_number':lambda *a: 0,
        'without_pagebreak':lambda *a: 0
    }

    def action_next(self, cr, uid, ids, context=None):
        """
        Print Survey Form(print template of the survey).

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for print survey form.
        """
        datas = {'ids' : self.read(cr, uid, ids, ['survey_ids'], context=context)[0]['survey_ids']}
        res = self.read(cr, uid, ids, ['survey_title', 'orientation', 'paper_size',\
                             'page_number', 'without_pagebreak'], context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'survey.print'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'survey.form',
            'datas': datas,
        }
survey_print()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
