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

from openerp.osv import fields, osv

class survey_browse_answer(osv.osv_memory):
    _name = 'survey.browse.answer'

    _columns = {
        'survey_id': fields.many2one('survey', "Survey", required="1"),
        'response_id': fields.many2one("survey.response", "Survey Answers", help="If this field is empty, all answers of the selected survey will be print."),
    }

    def action_next(self, cr, uid, ids, context=None):
        """
        Open Browse Response wizard. if you select only survey_id then this wizard open with all response_ids and 
        if you select survey_id and response_id then open the particular response of the survey.
        """
        if context is None: context = {}
        record = self.read(cr, uid, ids, [])
        record = record and record[0] or {} 
        if record['response_id']:
            res_id = [(record.get('response_id') and record['response_id'][0])]
        else:
            sur_response_obj = self.pool.get('survey.response')
            res_id = sur_response_obj.search(cr, uid, [('survey_id', '=', record['survey_id'][0])])
        context.update({'active' : True,'survey_id' : record['survey_id'][0], 'response_id' : res_id, 'response_no' : 0})
        search_obj = self.pool.get('ir.ui.view')
        search_id = search_obj.search(cr,uid,[('model','=','survey.question.wiz'),('name','=','Survey Search')])
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'search_view_id':search_id[0],
            'context' : context
         }

survey_browse_answer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
