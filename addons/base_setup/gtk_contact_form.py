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
from operator import itemgetter

from osv import osv, fields
import netsvc
import tools
from tools import misc

class base_gtkcontactform(osv.osv_memory):
    """
    """
    _name = 'base.gtkcontactform'
    _inherit = 'res.config'
    logger = netsvc.Logger()

    def default_get(self, cr, uid, fields_list=None, context=None):
         ''' set email and phone number selected in the previous company information
             form '''
         defaults = super(base_gtkcontactform, self)\
         .default_get(cr, uid, fields_list=fields_list, context=context)
         company_id = self.pool.get('base.setup.company').search(cr, uid, [])
         company = self.pool.get('base.setup.company').read(cr, uid, company_id)
         company = company and company[0] or False
         if company:
             defaults.update({'email':company.get('email',''),
                          'phone': company.get('phone','')})
         return defaults

    _columns = {
             'name':fields.char('Your Name', size=64, required=True),
             'job':fields.char('Job Title', size=64,),
             'email':fields.char('E-mail', size=64, required=True),
             'phone':fields.char('Phone', size=64, required=True),
             'total_employees':fields.selection([('1-5','1-5'),('5-20','5-20'),('20-100','20-100'),('100-500','100-500'),('500','500+')], 'No Of Employees', size=32),
             'industry':fields.selection([('apparel','Apparel'),('banking','Banking'),('biotechnology','Biotechnology'),('chemicals','Chemicals'),('communications','Communications'),
                                          ('construction','Construction'),('consulting','Consulting'),('education','Education'),('electronics','Electronics'),('energy','Energy'),('engineering','Engineering'),
                                          ('entertainment','Entertainment'),('environmental','Environmental'),('finance','Finance'),('government','Government'),('healthcare','Healthcare'),('hospitality','Hospitality'),
                                          ('insurance','Insurance'),('machinery','Machinery'),('manufacturing','Manufacturing'),('media','Media'),('notforprofit','Not For Profit'),
                                          ('recreation','Recreation'),('retail','Retail'),('shipping','Shipping'),('technology','Technology'),('telecommunications','Telecommunications'),
                                          ('transportation','Transportation'),('utilities','Utilities'),('other','Other'),
                                          ], 'Industry', size=32),
             'use_openerp':fields.boolean('We plan to use OpenERP'),
             'already_using_openerp':fields.boolean('Already using OpenERP'),
             'sell_openerp':fields.boolean('Plan to sell OpenERP'),
             'already_selling__openerp':fields.boolean('Already selling OpenERP'),

             'features':fields.boolean('The features of OpenERP'),
             'saas':fields.boolean('OpenERP Online Solutions (SaaS)'),
             'partners_program':fields.boolean('OpenERP Partners Program (for integrators)'),
             'support':fields.boolean('Support and Maintenance Solutions'),
             'training':fields.boolean('OpenERP Training Program'),
             'other':fields.boolean('Other'),
             'ebook':fields.boolean('ebook'),
             'updates':fields.boolean('updates'),
             }
    def execute(self, cr, uid, ids, context=None):
        company_id = self.pool.get('base.setup.company').search(cr, uid, [])
        company_data = self.pool.get('base.setup.company').read(cr, uid, company_id)
        company_data = company_data and company_data[0] or False
        country1 = ''
        if company_data and company_data.get('country_id', False):
            country = self.pool.get('res.country').read(cr, uid, company_data['country_id'],['name'])['name']
        for res in self.read(cr, uid, ids):
            email = res.get('email','')
            result = "\ncompany: "+ str(company_data.get('name',''))
            result += "\nname: " + str(res.get('name',''))
            result += "\nphone: " + str(res.get('phone',''))
            result += "\ncity: " + str(company_data.get('city',''))
            result += "\ncountry: " + str(country)
            result += "\nindustry: " + str(res.get('industry', ''))
            result += "\ntotal_employees: " + str(res.get('total_employees', ''))
            result += "\nplan_use: " +  str(res.get('use_openerp', False))
            result += "\nsell_openerp: " + str(res.get('sell_openerp', False))
            result += "\nebook: " + str(res.get('ebook',False))
            result += "\ngtk: " + str(True)
        misc.upload_data(email, result, type='SURVEY')



base_gtkcontactform()