# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from osv import fields
from tools.translate import _

class survey_name_wiz(osv.osv_memory):
    _name = 'survey.name.wiz'

    def default_get(self, cr, uid, fields, context={}):
        """
        Set the default value in survey_id field. if open this wizard in survey form then set the default value in survey_id = active survey id.

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of Survey statistics IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for created survey statistics report
        """
        if not context:
            context = {}
        data = super(survey_name_wiz, self).default_get(cr, uid, fields, context)
        if context.has_key('survey_id'):
            data['survey_id'] = context.get('survey_id',False)
        return data

    def _get_survey(self, cr, uid, context=None):
        """
        Set the value In survey_id field.

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey statistics IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value for created survey statistics report
        """
        surv_obj = self.pool.get("survey")
        result = []
        if context.has_key('survey_id'):
            for sur in surv_obj.browse(cr, uid, [context.get('survey_id',False)]):
                result.append((sur.id, sur.title))
            return result
        group_id = self.pool.get('res.groups').search(cr, uid, [('name', '=', 'Survey / Manager')])
        user_obj = self.pool.get('res.users')
        user_rec = user_obj.read(cr, uid, uid)
        for sur in surv_obj.browse(cr, uid, surv_obj.search(cr, uid, [])):
            if sur.state == 'open':
                if group_id[0]  in user_rec['groups_id']:
                    result.append((sur.id, sur.title))
                elif sur.id in user_rec['survey_id']:
                    result.append((sur.id, sur.title))
        return result

    _columns = {
        'survey_id': fields.selection(_get_survey, "Survey", required="1"),
        'page_no': fields.integer('Page Number'),
        'note': fields.text("Description"),
        'page': fields.char('Page Position',size = 12),
        'transfer': fields.boolean('Page Transfer'),
        'store_ans': fields.text('Store Answer'),
        'response': fields.char('Answer',size=16)
    }
    _defaults = {
        'page_no': lambda * a: - 1,
        'page': lambda * a: 'next',
        'transfer': lambda * a: 1,
        'response': lambda * a: 0,
    }

    def action_next(self, cr, uid, ids, context=None):
        """
        Start the survey, Increment in started survey field but if set the max_response_limit of
        survey then check the current user how many times start this survey. if current user max_response_limit
        is reach then this user can not start this survey(Raise Exception).

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for open survey question wizard.
        """
        survey_obj = self.pool.get('survey')
        search_obj = self.pool.get('ir.ui.view')

        sur_id = self.read(cr, uid, ids, [])[0]
        survey_id = sur_id['survey_id']
        context.update({'survey_id': survey_id, 'sur_name_id': sur_id['id']})
        cr.execute('select count(id) from survey_history where user_id=%s\
                    and survey_id=%s' % (uid,survey_id))

        res = cr.fetchone()[0]
        user_limit = survey_obj.read(cr, uid, survey_id, ['response_user'])['response_user']
        if user_limit and res >= user_limit:
            raise osv.except_osv(_('Warning !'),_("You can not give response for this survey more than %s times") % (user_limit))

        sur_rec = survey_obj.read(cr,uid,self.read(cr,uid,ids)[0]['survey_id'])
        if sur_rec['max_response_limit'] and sur_rec['max_response_limit'] <= sur_rec['tot_start_survey']:
            raise osv.except_osv(_('Warning !'),_("You can not give more response. Please contact the author of this survey for further assistance."))

        search_id = search_obj.search(cr,uid,[('model','=','survey.question.wiz'),('name','=','Survey Search')])

        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'search_view_id': search_id[0],
            'context': context
         }

    def on_change_survey(self, cr, uid, ids, survey_id, context=None):
        """
            on change event of survey_id field, if note is available in selected survey then display this note in note fields.

            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Survey IDs
            @param context: A standard dictionary for contextual values
            @return : Dictionary values of notes fields.
        """
        notes = self.pool.get('survey').read(cr, uid, survey_id, ['note'])['note']
        return {'value': {'note': notes}}

survey_name_wiz()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
