# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import openerp.netsvc as netsvc
from openerp.tools import copy
from openerp.tools.misc import UpdateableStr, UpdateableDict
from openerp.tools.translate import translate
from lxml import etree

import openerp.pooler as pooler

from openerp.osv.osv import except_osv
from openerp.osv.orm import except_orm
from openerp.netsvc import Logger, LOG_ERROR
import sys

class except_wizard(Exception):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.args = (name, value)

class interface(netsvc.Service):
    states = {}

    def __init__(self, name):
        assert not self.exists('wizard.'+name), 'The wizard "%s" already exists!' % (name,)
        super(interface, self).__init__('wizard.'+name)
        self.wiz_name = name

    def translate_view(self, cr, node, state, lang):
        if node.get('string'):
            trans = translate(cr, self.wiz_name+','+state, 'wizard_view', lang, node.get('string').encode('utf8'))
            if trans:
                node.set('string', trans)
        for n in node:
            self.translate_view(cr, n, state, lang)

    def execute_cr(self, cr, uid, data, state='init', context=None):
        if not context:
            context={}
        res = {}
        try:
            state_def = self.states[state]

            result_def = state_def.get('result', {})
            
            actions_res = {}
            # iterate through the list of actions defined for this state
            for action in state_def.get('actions', []):
                # execute them
                action_res = action(self, cr, uid, data, context)
                assert isinstance(action_res, dict), 'The return value of wizard actions should be a dictionary'
                actions_res.update(action_res)
                
            res = copy.copy(result_def)
            res['datas'] = actions_res
            
            lang = context.get('lang', False)
            if result_def['type'] == 'action':
                res['action'] = result_def['action'](self, cr, uid, data, context)
            elif result_def['type'] == 'form':
                fields = copy.deepcopy(result_def['fields'])
                arch = copy.copy(result_def['arch'])
                button_list = copy.copy(result_def['state'])

                if isinstance(fields, UpdateableDict):
                    fields = fields.dict
                if isinstance(arch, UpdateableStr):
                    arch = arch.string

                # fetch user-set defaut values for the field... shouldn't we pass it the uid?
                ir_values_obj = pooler.get_pool(cr.dbname).get('ir.values')
                defaults = ir_values_obj.get(cr, uid, 'default', False, [('wizard.'+self.wiz_name, False)])
                default_values = dict([(x[1], x[2]) for x in defaults])
                for val in fields.keys():
                    if 'default' in fields[val]:
                        # execute default method for this field
                        if callable(fields[val]['default']):
                            fields[val]['value'] = fields[val]['default'](uid, data, state)
                        else:
                            fields[val]['value'] = fields[val]['default']
                        del fields[val]['default']
                    else:
                        # if user has set a default value for the field, use it
                        if val in default_values:
                            fields[val]['value'] = default_values[val]
                    if 'selection' in fields[val]:
                        if not isinstance(fields[val]['selection'], (tuple, list)):
                            fields[val] = copy.copy(fields[val])
                            fields[val]['selection'] = fields[val]['selection'](self, cr, uid, context)
                        elif lang:
                            res_name = "%s,%s,%s" % (self.wiz_name, state, val)
                            trans = lambda x: translate(cr, res_name, 'selection', lang, x) or x
                            for idx, (key, val2) in enumerate(fields[val]['selection']):
                                fields[val]['selection'][idx] = (key, trans(val2))

                if lang:
                    # translate fields
                    for field in fields:
                        res_name = "%s,%s,%s" % (self.wiz_name, state, field)

                        trans = translate(cr, res_name, 'wizard_field', lang)
                        if trans:
                            fields[field]['string'] = trans

                        if 'help' in fields[field]:
                            t = translate(cr, res_name, 'help', lang, fields[field]['help']) 
                            if t:
                                fields[field]['help'] = t

                    # translate arch
                    if not isinstance(arch, UpdateableStr):
                        doc = etree.XML(arch)
                        self.translate_view(cr, doc, state, lang)
                        arch = etree.tostring(doc)

                    # translate buttons
                    button_list = list(button_list)
                    for i, aa  in enumerate(button_list):
                        button_name = aa[0]
                        trans = translate(cr, self.wiz_name+','+state+','+button_name, 'wizard_button', lang)
                        if trans:
                            aa = list(aa)
                            aa[1] = trans
                            button_list[i] = aa
                    
                res['fields'] = fields
                res['arch'] = arch
                res['state'] = button_list

            elif result_def['type'] == 'choice':
                next_state = result_def['next_state'](self, cr, uid, data, context)
                return self.execute_cr(cr, uid, data, next_state, context)
        
        except Exception, e:
            if isinstance(e, except_wizard) \
                or isinstance(e, except_osv) \
                or isinstance(e, except_orm):
                netsvc.abort_response(2, e.name, 'warning', e.value)
            else:
                import traceback
                tb_s = reduce(lambda x, y: x+y, traceback.format_exception(
                    sys.exc_type, sys.exc_value, sys.exc_traceback))
                logger = Logger()
                logger.notifyChannel("web-services", LOG_ERROR,
                        'Exception in call: ' + tb_s)
                raise

        return res

    def execute(self, db, uid, data, state='init', context=None):
        if not context:
            context={}
        cr = pooler.get_db(db).cursor()
        try:
            try:
                res = self.execute_cr(cr, uid, data, state, context)
                cr.commit()
            except Exception:
                cr.rollback()
                raise
        finally:
            cr.close()
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

