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

class survey_browse_answer(osv.osv_memory):
    _name = 'survey.browse.answer'
    
    def _get_survey(self, cr, uid, context=None):
        """
        Set the value in survey_id field,
       
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param context: A standard dictionary for contextual values,
        @return : Tuple in list with values.
        """        
        surv_obj = self.pool.get("survey")
        surv_resp_obj = self.pool.get("survey.response")
        result = []
        for sur in surv_obj.browse(cr, uid, surv_obj.search(cr, uid, [])):
            if surv_resp_obj.search(cr, uid, [('survey_id', '=', sur.id)]):
                result.append((sur.id, sur.title))
        return result

    _columns = {
        'survey_id': fields.selection(_get_survey, "Survey", required="1"),
        'response_id': fields.many2one("survey.response", "Survey Answers", help="If this field is empty, all answers of the selected survey will be print."),
    }

    def action_next(self, cr, uid, ids, context=None):
        """
        Open Browse Response wizard. if you select only survey_id then this wizard open with all response_ids and 
        if you select survey_id and response_id then open the particular response of the survey.
       
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of survey.browse.answer IDs,
        @param context: A standard dictionary for contextual values,
        @return : Dictionary value for Open the browse answer wizard.
        """
        if context is None: context = {}
        record = self.read(cr, uid, ids, [])
        record = record and record[0] or {} 
        if record['response_id']:
            res_id = [(record['response_id'])]
        else:
            sur_response_obj = self.pool.get('survey.response')
            res_id = sur_response_obj.search(cr, uid, [('survey_id', '=',int(record['survey_id']))])
        context.update({'active' : True,'survey_id' : record['survey_id'], 'response_id' : res_id, 'response_no' : 0})
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
