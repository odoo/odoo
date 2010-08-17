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
import urllib
import urllib2
import simplejson as json
import time

from osv import fields, osv

mailchimp_url = 'http://%s.api.mailchimp.com/1.2'

class mailchimp_account(osv.osv):
    _name = "mailchimp.account"

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
        url = mailchimp_url%mailchimp_account.data_center+ '/?method=%s'%method
        params = urllib.urlencode(params, doseq=True)
        response = urllib2.urlopen(url, params)
        return  json.loads(response.read())

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

    def add_partner_list(self, cr, uid, account_id, list_id,  partner_ids):
        vals = {} # just dictionary with partner_id and updated in list or not
        for partner in self.pool.get('res.partner').browse(cr, uid, partner_ids):
            params = {
                'id' : list_id,
                'email_address' : partner.email,
                'email_type':'text',
                'merge_vars[FNAME]':partner.name ,
                'merge_vars[date]' : time.strftime('%Y-%m-%d'),
                'merge_vars[phone]' : partner.phone,
                'merge_vars[website]' : partner.website,
                'merge_vars[address][country]' : partner.country.code,
                'merge_vars[address][city]' : partner.city,
                'double_optin':False
            }
            vals[partner.id] = self.get_response(cr, uid, account_id,
                                                         'listSubscribe', params)
        return vals

mailchimp_account()

class mailchimp_list(osv.osv_memory):
    _name = "mailchimp.list"
    _description = "Mailchimp list"

    _columns = {
        'mailchimp_account_id': fields.many2one('mailchimp.account',
                                             'Mailchimp Account', required=True),
        'name': fields.char('Name', size=64)
    }

mailchimp_list()

class marketing_campaign(osv.osv):
    _inherit = "marketing.campaign"

    _columns = {
        'mailchimp_account_id': fields.many2one(
                        'mailchimp.account', 'Account'),
        'mailchimp_campaign': fields.char('campaign', size=64),
    }
marketing_campaign()


class marketing_campaign_activity(osv.osv):
    _inherit = "marketing.campaign.activity"

    _columns = {
        'mailchimp_account_id': fields.many2one(
                        'mailchimp.account', 'Account'),
        'mailchimp_list': fields.char('List', size=64),
    }

    def onchange_mailchimp(self, cr, uid, ids, mailchimp_account_id):
        if mailchimp_account_id:
            return {'value':{'mailchimp_list':''}}
        return {'value':{}}

    def onchange_mailchimp_list(self, cr, uid, ids, mailchimp_account_id,
                                                                mailchimp_list):
        if mailchimp_account_id and mailchimp_list:
            lists = self.pool.get('mailchimp.account').get_response(cr,
                                             uid, mailchimp_account_id, 'lists')
            list_names = [l['name'] for l in lists]
            if mailchimp_list not in list_names:
                raise osv.except_osv('Error!!!',"Lists doesn't exists")
        else :
            return {}
        return {'value':{}}

    def _process_wi_mailchimp(self, cr, uid, activity, workitem, context=None):
        mailchimp_account_id = activity.mailchimp_account_id.id
        list_name = activity.mailchimp_list
        mc_acc_obj = self.pool.get('mailchimp.account')
        lists = mc_acc_obj.get_response(cr, uid, mailchimp_account_id, 'lists')
        list_id = ''
        for l in lists :
            if l['name'] == list_name:
                list_id = l['id']
                break;
        res_model = workitem.object_id.model
        res_id = workitem.res_id
        model_obj = self.pool.get(res_model).browse(cr, uid, res_id)
        params ={}
        if res_model == 'res.partner' :
            params.update({
                'email_address' : model_obj.email,
                'merge_vars[FNAME]':model_obj.name and model_obj.name or '',
                'merge_vars[website]' : model_obj.website,
                'merge_vars[address][country]' : model_obj.country.code,
            })
        elif res_model == 'crm.lead' :
            params.update({
                'email_address' : model_obj.email_from,
                'merge_vars[FNAME]':model_obj.partner_name and \
                                    model_obj.partner_name or '',
                'merge_vars[address][country]' : model_obj.country_id and \
                                            model_obj.country_id.code or ''
            })
        if params['email_address'] :
            user = mc_acc_obj.get_response(cr, uid, mailchimp_account_id,
                                     'listMemberInfo', {
                                        'id' : list_id,
                                        'email_address': params['email_address']
                                    })
            # if there s no user with the specify email it will return error code
            # and thus we add that user otherwise user is alredy subscribe and there
            # is no need to subscribe user again
            if 'error' in user:
                params.update({
                    'id' : list_id,
                    'email_type':'text',
                    'double_optin':False,
                    'merge_vars[date]' : time.strftime('%Y-%m-%d'),
                    'merge_vars[address][city]' : model_obj.city and model_obj.city or '',
                    'merge_vars[phone]' : model_obj.phone and model_obj.phone or '',
                })
                mc_acc_obj.get_response(cr, uid, mailchimp_account_id, 'listSubscribe', params)
                # TODO handle mailchimp error
            return True
        else :
            return {'error_msg' : "Invalid Email Address"}

    def __init__(self, *args):
        super(marketing_campaign_activity, self).__init__(*args)
        self._action_types.append(('mailchimp', 'Mailchimp'))

marketing_campaign_activity()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
