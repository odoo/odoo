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

from osv import fields, osv

import urllib2
import simplejson as json

mailchimp_url = 'http://%s.api.mailchimp.com/1.2'

class marketing_campaign_mailchimp_account(osv.osv): #{{{
    _name = "marketing.campaign.mailchimp.account"
    
    _columns = {
            'name': fields.char('Account Name', size=64),
            'username': fields.char('Username', size=64, required=True),
            'password': fields.char('Password', size=64, required=True),
            'apikey': fields.char('API Key', size=128),
            'data_center': fields.selection([('us1', 'US1'), ('us2', 'US2'), 
                                            ('uk1', 'UK1')], 'Data Center'),
            'state': fields.selection([('draft', 'Draft'), ('approved', 'Approved'), 
                           ('cancelled', 'Cancelled')], 'State', readonly=True)
        }
    
    _defaults = {
            'state': lambda *a: 'draft'
        }
    
    def get_response(self, cr, uid, mailchimp_id, method, params={}):
        mailchimp_account = self.browse(cr, uid, mailchimp_id)
        params['output'] = 'json'
        if method == 'login':
                params['username'] = mailchimp_account.username
                params['password'] = mailchimp_account.password
        else :
                params['apikey'] = mailchimp_account.apikey
        params = '&'.join(map(lambda x : '%s=%s' %(x, params[x]), params))
        url = mailchimp_url%mailchimp_account.data_center+ '/?method=%s'%method
        req = urllib2.Request(url, params)
        handle = urllib2.urlopen(req)
        response = json.loads(handle.read())
        return response 
    
    def button_approve(self, cr, uid, ids, context):
        acc_obj = self.browse(cr, uid, ids)[0]
        vals = {}
        if not acc_obj.apikey:
            method = 'login'
        else:
            method = 'ping'
        response = self.get_response(cr, uid, acc_obj.id, method)
        if 'error' not in response:
            if method == 'login' :
                vals['apikey'] = response
            vals['state'] = 'approved'
            self.write(cr, uid, ids, vals)
        else : 
            raise osv.except_osv('Error!!!',
                            "Can't approved accoutnt : %s"%response['error'])
        return True
    
    def button_cancel(self, cr, uid, ids, context):
        self.write(cr, uid, ids, {'state': 'cancelled'})
        return True
    
marketing_campaign_mailchimp_account() #}}}

#class marketing_campaign_mailchimp_list(osv.osv_memory): #{{{
#    _name = "marketing.campaign.mailchimp.list"
#    
#    _columns = {
#            'name': fields.char('Name', size=64),
#            'mailchimp_account_id': fields.many2one('marketing.campaign.mailchimp.account', 'Account'),
#            'list_id': fields.char('List Id', size=64,),
#        }
#    
#    _defaults = {
#            'state': lambda *a: 'draft'
#        }
#    
#marketing_campaign_mailchimp_list() #}}}

class marketing_campaign_segment(osv.osv): #{{{
    _inherit = "marketing.campaign.segment"
    
    _columns = {
            'synchro': fields.boolean('Mailchimp Synchro'),
            'mailchimp_account_id': fields.many2one(
                            'marketing.campaign.mailchimp.account', 'Account'),
            'mailchimp_list': fields.char('List', size=64),
        }
    
    def onchange_mailchimp(self, cr, uid, ids, mailchimp_account_id):
        if mailchimp_account_id:
            return {'value':{'mailchimp_list':''}}
        return {'value':{}}
    
    def onchange_mailchimp_list(self, cr, uid, ids, mailchimp_account_id, 
                                                                mailchimp_list):
        if mailchimp_account_id and mailchimp_list:
            lists = self.pool.get('marketing.campaign.mailchimp.account').get_response(cr,
                                             uid, mailchimp_account_id, 'lists')
            list_names = [list['name'] for list in lists]
            if mailchimp_list not in list_names:
                raise osv.except_osv('Error!!!',"Lists doesn't exists")
        else :
            return {}
        return {'value':{}}
marketing_campaign_segment() #}}}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
