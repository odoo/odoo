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
import os

import pooler
import osv
import tools
from tools import config
from tools.translate import _
from osv import osv, fields

class abstract_quality_check(object):
    '''
        This Class is abstract class for all test
    '''

    def __init__(self):
        '''
        this method should initialize the variables
        '''
        #This float have to store the rating of the module.
        #Used to compute the final score (average of all scores).
        #0 <= self.score <= 1
        self.score = 0.0

        #This char have to store the name of the test.
        self.name = ""

        #This char have to store the aim of the test and eventually a note.
        self.note = ""

        #This char have to store the result.
        #Used to display the result of the test.
        self.result = ""

        #This char have to store the result with more details.
        #Used to provide more details if necessary.
        self.result_details = ""

        # This boolean variable defines that if you do not want to calculate score and just only need detail
        # or summary report for some test then you will make it False.
        self.bool_count_score = True

        #This bool defines if the test can be run only if the module
        #is installed.
        #True => the module have to be installed.
        #False => the module can be uninstalled.
        self.bool_installed_only = True

        #This variable is used to give result of test more weight,
        #because some tests are more critical than others.
        self.ponderation = 1.0

        #Specify test got an error on module
        self.error = False

        #Specify the minimal score for the test (in percentage(%))
        self.min_score = 50

        #Specify whether test should be consider for Quality checking of the module
        self.active = True

        #This variable used to give message if test result is good or not
        self.message = ''

        #The tests have to subscribe itselfs in this list, that contains
        #all the test that have to be performed.
        self.tests = []
        self.list_folders = os.listdir(config['addons_path'] +
            '/base_module_quality/')
        for item in self.list_folders:
            self.item = item
            path = config['addons_path']+'/base_module_quality/'+item
            if os.path.exists(path + '/' + item + '.py') and item not in ['report', 'wizard', 'security']:
                item2 = 'base_module_quality.' + item +'.' + item
                x_module = __import__(item2)
                x_file = getattr(x_module, item)
                x_obj = getattr(x_file, item)
                self.tests.append(x_obj)
#        raise 'Not Implemented'

    def run_test(self, cr, uid, module_path=""):
        '''
        this method should do the test and fill the score, result and result_details var
        '''
        raise osv.except_osv(_('Programming Error'), _('Test Is Not Implemented'))

    def get_objects(self, cr, uid, module):
        # This function returns all object of the given module..
        pool = pooler.get_pool(cr.dbname)
        ids2 = pool.get('ir.model.data').search(cr, uid,
            [('module', '=', module), ('model', '=', 'ir.model')])
        model_list = []
        model_data = pool.get('ir.model.data').browse(cr, uid, ids2)
        for model in model_data:
            model_list.append(model.res_id)
        obj_list = []
        for mod in pool.get('ir.model').browse(cr, uid, model_list):
            obj_list.append(str(mod.model))
        return obj_list

    def get_model_ids(self, cr, uid, models=[]):
        # This function returns all ids of the given objects..
        if not models:
            return []
        pool = pooler.get_pool(cr.dbname)
        return pool.get('ir.model').search(cr, uid, [('model', 'in', models)])

    def get_ids(self, cr, uid, object_list):
        #This method return dictionary with ids of records of object for module
        pool = pooler.get_pool(cr.dbname)
        result_ids = {}
        for obj in object_list:
            ids = pool.get(obj).search(cr, uid, [])
            ids = filter(lambda id: id != None, ids or [])
            result_ids[obj] = ids
        return result_ids

    def format_table(self, header=[], data_list={}): #This function can work forwidget="text_wiki"
        detail = ""
        detail += (header[0]) % tuple(header[1])
        frow = '\n|-'
        for i in header[1]:
            frow += '\n| %s'
        for key, value in data_list.items():
            detail += (frow) % tuple(value)
        detail = detail + '\n|}'
        return detail

    def format_html_table(self, header=[], data_list=[]): #This function can work for widget="html_tag"
        # function create html table....
        detail = ""
        detail += (header[0]) % tuple(header[1])
        frow = '<tr>'
        for i in header[1]:
            frow += '<td>%s</td>'
        frow += '</tr>'
        for key, value in data_list.items():
            detail += (frow) % tuple(value)
        return detail

    def add_quatation(self, x_no, y_no):
        return x_no/y_no

    def get_style(self):
        # This function return style tag with specified styles for html pages
        style = '''
            <style>
                .divstyle {
                    border:1px solid #aaaaaa;
                    background-color:#f9f9f9;
                    padding:5px;
                }
                .tablestyle {
                    border:1px dashed gray;
                }
                .tdatastyle {
                    border:0.5px solid gray;
                }
                .head {
                    color: black;
                    background: none;
                    font-weight: normal;
                    margin: 0;
                    padding-top: .5em;
                    padding-bottom: .17em;
                    border-bottom: 1px solid #aaa;
                }
          </style> '''
        return style


class module_quality_check(osv.osv):
    _name = 'module.quality.check'
    _columns = {
        'name': fields.char('Rated Module', size=64, ),
        'final_score': fields.char('Final Score (%)', size=10,),
        'check_detail_ids': fields.one2many('module.quality.detail', 'quality_check_id', 'Tests',)
    }

    def check_quality(self, cr, uid, module_name, module_state=None):
        '''
        This function will calculate score of openerp module
        It will return data in below format:
            Format: {'final_score':'80.50', 'name': 'sale',
                    'check_detail_ids':
                        [(0,0,{'name':'workflow_test', 'score':'100', 'ponderation':'0', 'summary': text_wiki format data, 'detail': html format data, 'state':'done', 'note':'XXXX'}),
                        ((0,0,{'name':'terp_test', 'score':'60', 'ponderation':'1', 'summary': text_wiki format data, 'detail': html format data, 'state':'done', 'note':'terp desctioption'}),
                         ..........]}
        So here the detail result is in html format and summary will be in text_wiki format.
        '''
        #list_folders = os.listdir(config['addons_path']+'/base_module_quality/')
        pool = pooler.get_pool(cr.dbname)
        obj_module = pool.get('ir.module.module')
        if not module_state:
            module_id = obj_module.search(cr, uid, [('name', '=', module_name)])
            if module_id:
                module_state = obj_module.browse(cr, uid, module_id[0]).state

        abstract_obj = abstract_quality_check()
        score_sum = 0.0
        ponderation_sum = 0.0
        create_ids = []
        for test in abstract_obj.tests:
            ad = tools.config['addons_path']
            if module_name == 'base':
                ad = tools.config['root_path']+'/addons'
            module_path = os.path.join(ad, module_name)
            val = test.quality_test()
            if val.active:
                if not val.bool_installed_only or module_state == "installed":
                    val.run_test(cr, uid, str(module_path))
                    if not val.error:
                        data = {
                            'name': val.name,
                            'score': val.score * 100,
                            'ponderation': val.ponderation,
                            'summary': val.result,
                            'detail': val.result_details,
                            'state': 'done',
                            'note': val.note,
                            'message': val.message
                        }
                        if val.bool_count_score:
                            score_sum += val.score * val.ponderation
                            ponderation_sum += val.ponderation
                    else:
                        data = {
                            'name': val.name,
                            'score': 0,
                            'summary': val.result,
                            'state': 'skipped',
                            'note': val.note,
                        }
                else:
                    data = {
                        'name': val.name,
                        'note': val.note,
                        'score': 0,
                        'state': 'skipped',
                        'summary': _("The module has to be installed before running this test.")
                    }
                create_ids.append((0, 0, data))
        final_score = ponderation_sum and '%.2f' % (score_sum / ponderation_sum * 100) or 0
        data = {
            'name': module_name,
            'final_score': final_score,
            'check_detail_ids' : create_ids,
        }
        return data

module_quality_check()

class module_quality_detail(osv.osv):
    _name = 'module.quality.detail'
    _columns = {
        'quality_check_id': fields.many2one('module.quality.check', 'Quality'),
        'name': fields.char('Name',size=128),
        'score': fields.float('Score (%)'),
        'ponderation': fields.float('Ponderation', help='Some tests are more critical than others, so they have a bigger weight in the computation of final rating'),
        'note': fields.text('Note'),
        'summary': fields.text('Summary'),
        'detail': fields.text('Details'),
        'message': fields.char('Message', size=64),
        'state': fields.selection([('done','Done'),('skipped','Skipped'),], 'State', size=6, help='The test will be completed only if the module is installed or if the test may be processed on uninstalled module.'),
    }

module_quality_detail()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
