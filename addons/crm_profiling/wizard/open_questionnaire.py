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
from tools.translate import _

class open_questionnaire(osv.osv_memory):
    _name = 'open.questionnaire'
    _columns = {
        'questionnaire_id': fields.many2one('crm_profiling.questionnaire', 'Questionnaire name', required=True),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(open_questionnaire, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.has_key('form') and context.has_key('fields'):
            field  = {}
            form = context.get('form')
            form += """
                    <newline/>
                    <separator string="" colspan="4"/>
                    <group col="4" colspan="4">
                        <group col="2" colspan="2"/>
                        <button special="cancel" icon="gtk-cancel" string="Cancel"/>
                        <button name="questionnaire_compute" string="Save Data" icon="terp-stock_format-scientific" type="object"/>
                    </group>
                </form>
            """
            res['fields'] = context.get('fields')
            for key, value in res['fields'].items():
                 field[key] = fields.many2one('crm_profiling.answer', value['string'])
                 self._columns.update(field)
            res['arch'] = form
        return res


    def questionnaire_compute(self, cr, uid, ids, context=None):
        """ Adds selected answers in partner form """
        model = context.get('active_model')
        if model == 'res.partner':
            data = self.read(cr, uid, ids, context.get('fields').keys(), context=context)[0]
            self.pool.get(model)._questionnaire_compute(cr, uid, data, context=context)
        return {'type': 'ir.actions.act_window_close'}


    def build_form(self, cr, uid, ids, context=None):
        """ Dynamically generates form according to selected questionnaire """
        models_data = self.pool.get('ir.model.data')
        questionnaire_id = self.browse(cr, uid, ids, context=context)[0].questionnaire_id.id
        quest_form, quest_fields = self.pool.get('crm_profiling.questionnaire').build_form(cr, uid, questionnaire_id, context=context)
        context.update({
                        'form': quest_form,
                        'fields': quest_fields
        })

        result = models_data._get_id(cr, uid, 'crm_profiling', 'view_open_questionnaire_form')
        res_id = models_data.browse(cr, uid, result, context=context).res_id

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

