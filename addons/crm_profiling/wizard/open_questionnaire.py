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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class open_questionnaire_line(osv.osv_memory):
    _name = 'open.questionnaire.line'
    _rec_name = 'question_id'
    _columns = {
        'question_id': fields.many2one('crm_profiling.question','Question', required=True),
        'answer_id': fields.many2one('crm_profiling.answer', 'Answer'),
        'wizard_id': fields.many2one('open.questionnaire', 'Questionnaire'),
    }

open_questionnaire_line()

class open_questionnaire(osv.osv_memory):
    _name = 'open.questionnaire'
    _columns = {
        'questionnaire_id': fields.many2one('crm_profiling.questionnaire', 'Questionnaire name'),
        'question_ans_ids': fields.one2many('open.questionnaire.line', 'wizard_id', 'Question / Answers'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(open_questionnaire, self).default_get(cr, uid, fields, context=context)
        questionnaire_id = context.get('questionnaire_id', False)
        if questionnaire_id and 'question_ans_ids' in fields:
            query = """
                select question as question_id from profile_questionnaire_quest_rel where questionnaire = %s"""
            cr.execute(query, (questionnaire_id,))
            result = cr.dictfetchall()
            res.update(question_ans_ids=result)
        return res

    def questionnaire_compute(self, cr, uid, ids, context=None):
        """ Adds selected answers in partner form """
        model = context.get('active_model')
        answers = []
        if model == 'res.partner':
            data = self.browse(cr, uid, ids[0], context=context)
            for d in data.question_ans_ids:
                 if d.answer_id:
                     answers.append(d.answer_id.id)
            self.pool.get(model)._questionnaire_compute(cr, uid, answers, context=context)
        return {'type': 'ir.actions.act_window_close'}


    def build_form(self, cr, uid, ids, context=None):
        """ Dynamically generates form according to selected questionnaire """
        models_data = self.pool.get('ir.model.data')
        result = models_data._get_id(cr, uid, 'crm_profiling', 'open_questionnaire_form')
        res_id = models_data.browse(cr, uid, result, context=context).res_id
        datas = self.browse(cr, uid, ids[0], context=context)
        context.update({'questionnaire_id': datas.questionnaire_id.id})

        return {
            'name': _('Questionnaire'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'open.questionnaire',
            'type': 'ir.actions.act_window',
            'views': [(res_id,'form')],
            'target': 'new',
            'context': context
        }

open_questionnaire()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

