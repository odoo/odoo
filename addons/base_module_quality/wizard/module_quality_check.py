# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
import wizard
import pooler
from osv import osv, fields

import tools
import os

from base_module_quality import base_module_quality
#TODO: (utiliser les nouveaux wizards pour heriter la vue et rajouter un onglet par test?)
#TODO: implement the speed test
#TODO: add cheks: do the class quality_check inherits the class abstract_quality_check?
#TODO: improve translability
#TODO: clean


#To keep or not? to be discussed...

#~ view_form = """<?xml version="1.0"?>
#~ <form string="Check quality">
    #~ <notebook>
        #~ <page string="Summary">
            #~ <field name="general_info" widget="text_wiki" nolabel="1" colspan="4" height="350" width="800"/>
        #~ </page>
    #~ </notebook>
#~ </form>"""


#~ view_field = {
    #~ "general_info": {'type': 'text', 'string': 'General Info',  'readonly':True},
#~ }


class wiz_quality_check(osv.osv_memory):

#    general_info = ""
    _name = 'wizard.quality.check'

    def _check(self, cr, uid, data, context={}):
        string_ret = ""
        string_detail = ""
        from tools import config
        data['ids'] = data.get('module_id', False)
        pool = pooler.get_pool(cr.dbname)
        module_data = pool.get('ir.module.module').browse(cr, uid, [data['ids']])
        list_folders = os.listdir(config['addons_path']+'/base_module_quality/')
        module_name = module_data[0].name
        abstract_obj = base_module_quality.abstract_quality_check()
        for test in abstract_obj.tests:
            ad = tools.config['addons_path']
            if module_data[0].name == 'base':
                ad = tools.config['root_path']+'/addons'
            module_path = os.path.join(ad, module_data[0].name)
            val = test.quality_test()
            val.run_test(cr, uid, str(module_path), str(module_data[0].state))
            string_ret += val.result['summary']
            string_detail += val.result['detail']
        self.string_detail = string_detail
        return ""

    def _check_detail(self, cr, uid, data, context={}):
        return self.string_detail


#    def _general_info(self, cr, uid, data, context={}):
#        return self.general_info

    #~ states = {

        #~ 'init': {
            #~ 'actions': [_check],
            #~ 'result': {'type':'form', 'arch':view_form, 'fields':view_field, 'state':[('end','Ok')]},
        #~ },
        #~ }
#To keep or not? to be discussed...

        #~ 'init': {
            #~ 'actions': [],
            #~ 'result': {'type':'form', 'arch':form_check, 'fields':fields_check, 'state':[('end','Cancel'),('do','Do Test')]}
        #~ },
    _columns = {
#        'general_info': fields.text('General Info', readonly="1",),
#        'detail' : fields.text('Detail', readonly="0",),
        'verbose_detail' : fields.one2many('quality.check.detail', 'quality_check', 'Verbose Detail', readonly="0",)
    }
    _defaults = {
#        'general_info': _check,
#        'detail': _check_detail
        'verbose_detail': _check,
    }

wiz_quality_check()

class quality_check_detail(osv.osv_memory):
    _name = 'quality.check.detail'
    _rec_name = 'quality_check'
    _columns = {
        'quality_check': fields.many2one('wizard.quality.check', 'Quality'),
        'general_info': fields.text('General Info', readonly="1",),
        'detail' : fields.text('Detail', readonly="1",),
    }
quality_check_detail()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

