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
import wizard
import pooler
from osv import osv, fields

import tools
import os

from base_module_quality import base_module_quality

#TODO: add cheks: do the class quality_check inherits the class abstract_quality_check?


class wiz_quality_check(osv.osv):
    _name = 'wizard.quality.check'
    _columns = {
        'name': fields.char('Rated Module', size=64, ),
        'final_score': fields.char('Final Score (%)', size=10,),
        'test_ids' : fields.one2many('quality.check.detail', 'quality_check_id', 'Tests',)
    }
wiz_quality_check()


class quality_check_detail(osv.osv):
    _name = 'quality.check.detail'
    _columns = {
        'quality_check_id': fields.many2one('wizard.quality.check', 'Quality'),
        'name': fields.char('Name',size=128,),
        'score': fields.float('Score (%)',),
        'ponderation': fields.float('Ponderation',help='Some tests are more critical than others, so they have a bigger weight in the computation of final rating'),
        'summary': fields.text('Summary',),
        'detail' : fields.text('Details',),
        'state': fields.selection([('done','Done'),('skipped','Skipped'),], 'State', size=6, help='The test will be completed only if the module is installed or if the test may be processed on uninstalled module.'),
    }
quality_check_detail()


class create_quality_check(wizard.interface):

    def _create_quality_check(self, cr, uid, data, context={}):
        pool = pooler.get_pool(cr.dbname)
        print data, context
        objs = []
        for id in data['ids']:
            module_data = pool.get('ir.module.module').browse(cr, uid, id)
            #list_folders = os.listdir(config['addons_path']+'/base_module_quality/')
            abstract_obj = base_module_quality.abstract_quality_check()
            score_sum = 0.0
            ponderation_sum = 0.0
            create_ids = []
            for test in abstract_obj.tests:
                ad = tools.config['addons_path']
                if module_data.name == 'base':
                    ad = tools.config['root_path']+'/addons'
                module_path = os.path.join(ad, module_data.name)
                val = test.quality_test()

                if not val.bool_installed_only or module_data.state=="installed":
                    val.run_test(cr, uid, str(module_path))
                    data = {
                        'name': val.name,
                        'score': val.score * 100,
                        'ponderation': val.ponderation,
                        'summary': val.result,
                        'detail': val.result_details,
                        'state': 'done',
                    }
                    create_ids.append((0,0,data))
                    score_sum += val.score * val.ponderation
                    ponderation_sum += val.ponderation
                else:
                    data = {
                        'name': val.name,
                        'score': 0,
                        'state': 'skipped',
                        'summary': _("The module has to be installed before running this test.")
                    }
                    create_ids.append((0,0,data))

            final_score = str(score_sum / ponderation_sum * 100) + "%"
            data = {
                'name': module_data.name,
                'final_score': final_score,
                'test_ids' : create_ids,
            }
            obj = pool.get('wizard.quality.check').create(cr, uid, data, context)
            objs.append(obj)
        return objs

    def _open_quality_check(self, cr, uid, data, context):
        obj_ids = self._create_quality_check(cr, uid, data, context)
        return {
            'domain': "[('id','in', ["+','.join(map(str,obj_ids))+"])]",
            'name': _('Quality Check'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'wizard.quality.check',
            'type': 'ir.actions.act_window'
        }

    states = {
        'init' : {
            'actions' : [],
            'result': {'type':'action', 'action':_open_quality_check, 'state':'end'}
        }
    }

create_quality_check("create_quality_check_wiz")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

