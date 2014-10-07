# -*- coding: utf-8 -*-
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import Warning
from openerp import SUPERUSER_ID
from datetime import datetime, timedelta
from openerp.osv import osv, fields
import simplejson
from openerp.http import request


class Experiment_snapshot(osv.Model):
    _name = "website_version.experiment_snapshot"

    def _get_index(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for exp_snap in self.browse(cr, uid, ids, context=context):
            exp = exp_snap.experiment_id
            index = 1
            for x in exp.experiment_snapshot_ids:
                if x.id == exp_snap.id:
                    break
                else:
                    index+=1
            result[exp_snap.id] = index
        return result
    
    _columns = {
        'snapshot_id': fields.many2one('website_version.snapshot',string="Snapshot_id",required=True ,ondelete='cascade'),
        'experiment_id': fields.many2one('website_version.experiment',string="Experiment_id",required=True,ondelete='cascade'),
        'frequency': fields.selection([('10','Rare'),('50','Sometimes'),('100','Offen')], 'Frequency'),
        'google_index': fields.function(_get_index,type='integer', string='Google_index'),
    }

    _defaults = {
        'frequency': '10',
    }

class Goals(osv.Model):
    _name = "website_version.goals"
    
    _columns = {
        'name': fields.char(string="Name", size=256, required=True),
        'google_ref': fields.char(string="Reference Google", size=256, required=True),        
    }

EXPERIMENT_STATES = [('draft','Draft'),('ready_to_run', 'Ready to run'),('running','Running'),('ended','Ended')]

class Experiment(osv.Model):
    _name = "website_version.experiment"
    _inherit = ['mail.thread']

    def create(self, cr, uid, vals, context=None):
        print vals
        exp={}
        exp['name'] = vals['name']
        #exp['objectiveMetric'] = ["ga:adsenseAdsClicks","ga:adsenseAdsViewed","ga:adsenseRevenue","ga:bounces","ga:pageviews","ga:sessionDuration","ga:transactions","ga:transactionRevenue"]
        exp['objectiveMetric'] = self.pool['website_version.goals'].browse(cr, uid, [vals['objectives']],context)[0].google_ref
        #exp['objectiveMetric'] = "ga:adsenseAdsClicks"
        exp['status'] = vals['state']
        exp['variations'] =[{'name':'master','url': 'http://0.0.0.0:8069/master'}]
        l =  vals.get('experiment_snapshot_ids')
        if l:
            for snap in l:
                name = self.pool['website_version.snapshot'].browse(cr, uid, [snap[2]['snapshot_id']],context)[0].name
                exp['variations'].append({'name':name, 'url': 'http://0.0.0.0:8069/'+name})
        google_id = self.pool['google.management'].create_an_experiment(cr, uid, exp, vals['website_id'], context=context)
        if not google_id:
            raise Warning("Please verify you give the authorizations to use google analytics api ...")
        vals['google_id'] = google_id
        return super(Experiment, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        print vals
        name = vals.get('name')
        state = vals.get('state')
        exp_snaps = vals.get('experiment_snapshot_ids')
        obj_metric = vals.get('objectives')
        #some write operation doesn't need to synchronise with Google
        if name or state or exp_snaps or obj_metric:
            print 'WRITE EXP'
            for exp in self.browse(cr, uid, ids, context=context):
                temp={}
                if name:
                    temp['name'] = name
                else:
                    temp['name'] = exp.name
                if state:
                    current = self.pool['google.management'].get_experiment_info(cr, uid, exp.google_id, exp.website_id.id, context=None)
                    if len(current[1]["variations"]) == 1:
                        raise Warning("You must define at least one variation in your experiment.")
                    if not current[1].get("objectiveMetric"):
                        raise Warning("You must define at least one goal for this experiment in your Google Analytics account before moving its state.")
                    if current[1]["status"] == 'RUNNING' and (state == 'draft' or state == 'ready_to_run'):
                        raise Warning("You cannot modify a running experiment.")
                    if state == 'ended' and not current[1]["status"] == 'RUNNING':
                        raise Warning("Your experiment must be running to be ended.")
                    if current[1]["status"] == 'ENDED':
                        raise Warning("You cannot modify the state of an ended experiement.")
                    print current[1]["status"]
                    temp['status'] = state
                else:
                    temp['status'] = exp.state
                if obj_metric:
                    current = self.pool['google.management'].get_experiment_info(cr, uid, exp.google_id, exp.website_id.id, context=None)
                    if current[1]["status"] == 'RUNNING' or current[1]["status"] == 'ENDED':
                        raise Warning("You cannot modify the objective of an ended or running experiement.")
                    temp['objectiveMetric'] = self.pool['website_version.goals'].browse(cr, uid, [obj_metric],context)[0].google_ref
                if exp_snaps:
                    index = 0
                    temp['variations'] = [{'name':'master','url': 'http://0.0.0.0:8069/master'}]
                    for exp_s in exp.experiment_snapshot_ids:
                        for li in exp_snaps:
                            if not li[0] == 2 and li[1] == exp_s.id:
                                temp['variations'].append({'name':exp_s.snapshot_id.name, 'url': 'http://0.0.0.0:8069/'+exp_s.snapshot_id.name})
                        index+=1
                    while index< len(exp_snaps):
                        snap_id = exp_snaps[index][2]['snapshot_id']
                        snap_name = self.pool['website_version.snapshot'].browse(cr, uid, [snap_id], context=context)[0].name
                        temp['variations'].append({'name':snap_name, 'url': 'http://0.0.0.0:8069/'+snap_name})
                        index+=1
                else:
                    temp['variations'] = [{'name':'master','url': 'http://0.0.0.0:8069/master'}]
                    for exp_s in exp.experiment_snapshot_ids:
                        temp['variations'].append({'name':exp_s.snapshot_id.name, 'url': 'http://0.0.0.0:8069/'+exp_s.snapshot_id.name})
                #to check the constraints before to write on the google analytics account
                print temp 
                x = super(Experiment, self).write(cr, uid, ids, vals, context=context)
                self.pool['google.management'].update_an_experiment(cr, uid, temp, exp.google_id, exp.website_id.id, context=None)
        else:
            x = super(Experiment, self).write(cr, uid, ids, vals, context=context)
        return x

    def unlink(self, cr, uid, ids, context=None):
        for exp in self.browse(cr, uid, ids, context=context):
            self.pool['google.management'].delete_an_experiment(cr, uid, exp.google_id, exp.website_id.id, context=context)
        return super(Experiment, self).unlink(cr, uid, ids, context=context)


    def _get_version_number(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for exp in self.browse(cr, uid, ids, context=context):
            result[exp.id] = 0
            sum_pond = 0
            for exp_snap in exp.experiment_snapshot_ids:
                    sum_pond += int(exp_snap.frequency)
                    result[exp.id] += 1
            if sum_pond < 100:
                #We must considerate master
                result[exp.id] += 1
        return result

    def _get_objective(self,cr,uid,ids,name,args,context=None):
        return [("ga:bounces","bounces"),("ga:pageviews","pageviews"),("ga:sessionDuration","sessionDuration")]

    def update_goals(self,cr,uid,ids,context=None):
        gm_obj = self.pool['google.management']
        goals_obj = self.pool['website_version.goals']
        ids = goals_obj.search(cr, uid, [],context=context)
        website_id = context.get('website_id')
        if not website_id:
            raise Warning("You must specify the website.")
        x = gm_obj.get_goal_info(cr, uid, website_id, context=context)
        #goals_obj.unlink(cr, uid, ids, context=context)
        for y in x[1]['items']:
            if not goals_obj.search(cr, uid, [('name','=',y['name'])],context=context):
                vals ={'name':y['name'], 'google_ref':'ga:goal'+y['id']+'Completions'}
                goals_obj.create(cr, uid, vals, context=None)


    
    _columns = {
        'name': fields.char(string="Title", size=256, required=True),
        'experiment_snapshot_ids': fields.one2many('website_version.experiment_snapshot', 'experiment_id',string="experiment_snapshot_ids"),
        'website_id': fields.many2one('website',string="Website", required=True),
        'state': fields.selection(EXPERIMENT_STATES, 'Status', required=True, copy=False, track_visibility='onchange'),
        'objectives': fields.many2one('website_version.goals',string="Objectives"),
        'color': fields.integer('Color Index'),
        'version_number' : fields.function(_get_version_number,type='integer'),
        'sequence': fields.integer('Sequence', required=True, help="Test."),
        'google_id': fields.char(string="Google_id", size=256),
    }

    _defaults = {
        'state': 'draft',
        'sequence': 1,
    }

    def _check_page(self, cr, uid, ids, context=None):
        exp_ids = self.search(cr,uid,[],context=context)
        exps = self.browse(cr,uid,exp_ids,context=context)
        check_a = set()
        check_b = set()
        for exp in exps:
            for exp_snap in exp.experiment_snapshot_ids:
                for view in exp_snap.snapshot_id.view_ids:
                    x = (view.key,view.website_id.id)
                    y = (view.key,view.website_id.id,exp_snap.experiment_id.id)
                    if x in check_a and not y in check_b and exp.state == 'running':
                        return False
                    elif exp.state == 'running':
                        check_a.add(x)
                        check_b.add(y)
        return True

    _constraints = [
        (_check_page, 'This experiment contains a page which is already used in another running experience', ['state']),
    ]

    _order = 'sequence'

    _group_by_full = {
        'state': lambda *args, **kwargs : ([s[0] for s in EXPERIMENT_STATES], dict()),
    }

class google_management(osv.AbstractModel):
    STR_SERVICE = 'management'
    
    _name = 'google.%s' % STR_SERVICE

    def generate_data(self, cr, uid, experiment, isCreating=False, context=None):
        
        data = {
            'name': experiment['name'],
            'status': experiment['status'],
            'variations': experiment['variations']
        }

        return data

    def create_an_experiment(self, cr, uid, data, website_id, context=None):
        gs_pool = self.pool['google.service']
        website = self.pool['website'].browse(cr, uid, website_id, context=context)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1] 
        profileId = website.google_analytics_view_id
        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments?access_token=%s' % (accountId, webPropertyId, profileId, self.get_token(cr, uid, context))
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)
        try:
            x = gs_pool._do_request(cr, uid, url, data_json, headers, type='POST', context=context)
        except:
            x = False
        return x[1]['id']

    def update_an_experiment(self, cr, uid, data, google_id, website_id, context=None):
        gs_pool = self.pool['google.service']
        website = self.pool['website'].browse(cr, uid, website_id, context=context)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1] 
        profileId = website.google_analytics_view_id

        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s?access_token=%s' % (accountId, webPropertyId, profileId, google_id, self.get_token(cr, uid, context))
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)

        return gs_pool._do_request(cr, uid, url, data_json, headers, type='PUT', context=context)

    def get_experiment_info(self, cr, uid, google_id, website_id, context=None):
        gs_pool = self.pool['google.service']
        website = self.pool['website'].browse(cr, uid, website_id, context=context)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1] 
        profileId = website.google_analytics_view_id

        params = {
            'access_token': self.get_token(cr, uid, context),
        }
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' % (accountId, webPropertyId, profileId, google_id)
        return gs_pool._do_request(cr, uid, url, params, headers, type='GET', context=context)

    def get_goal_info(self, cr, uid, website_id, context=None):
        gs_pool = self.pool['google.service']
        website = self.pool['website'].browse(cr, uid, website_id, context=context)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1] 
        profileId = website.google_analytics_view_id

        params = {
            'access_token': self.get_token(cr, uid, context),
        }
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/goals' % (accountId, webPropertyId, profileId)
        return gs_pool._do_request(cr, uid, url, params, headers, type='GET', context=context)

    def delete_an_experiment(self, cr, uid, google_id, website_id, context=None):
        gs_pool = self.pool['google.service']
        website = self.pool['website'].browse(cr, uid, website_id, context=context)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1] 
        profileId = website.google_analytics_view_id

        params = {
            'access_token': self.get_token(cr, uid, context)
        }
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' %(accountId, webPropertyId, profileId, google_id)

        return gs_pool._do_request(cr, uid, url, params, headers, type='DELETE', context=context)



    def get_list_account(self, cr, uid, context=None):
        token = self.get_token(cr, uid, context)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        params = {'access_token': token}

        url = "/analytics/v3/management/accounts"
        try:
            status, content, _ = self.pool['google.service']._do_request(cr, uid, url, params, headers, type='GET', context=context)
        except:
            raise Warning("ho my good, there are a bug")
            pass
        return content  # need to check status via returned code (see calendar)


    def get_token(self, cr, uid, context=None):
        icp = self.pool['ir.config_parameter']
        validity = icp.get_param(cr, SUPERUSER_ID, 'google_%s_token_validity' % self.STR_SERVICE)
        token = icp.get_param(cr, SUPERUSER_ID, 'google_%s_token' % self.STR_SERVICE)
        if datetime.strptime(validity.split('.')[0], DEFAULT_SERVER_DATETIME_FORMAT) < (datetime.now() + timedelta(minutes=3)):
            token = self.do_refresh_token(cr, uid, context=context)
        return token

    def do_refresh_token(self, cr, uid, context=None):
        gs_pool = self.pool['google.service']
        icp = self.pool['ir.config_parameter']

        rtoken = icp.get_param(cr, SUPERUSER_ID, 'google_%s_rtoken' % self.STR_SERVICE)
        all_token = gs_pool._refresh_google_token_json(cr, uid, rtoken, self.STR_SERVICE, context=context)

        icp.set_param(cr, SUPERUSER_ID, 'google_%s_token_validity' % self.STR_SERVICE, datetime.now() + timedelta(seconds=all_token.get('expires_in')))
        icp.set_param(cr, SUPERUSER_ID, 'google_%s_token' % self.STR_SERVICE, all_token.get('access_token'))
        return all_token.get('access_token')



    # Should be called at configuration
    def get_management_scope(self):
        return 'https://www.googleapis.com/auth/analytics https://www.googleapis.com/auth/analytics.edit'
        
    def authorize_google_uri(self, cr, uid, from_url='http://www.odoo.com', context=None):
        url = self.pool['google.service']._get_authorize_uri(cr, uid, from_url, self.STR_SERVICE, scope=self.get_management_scope(), context=context)
        return url

    # convert code from authorize into token
    def set_all_tokens(self, cr, uid, authorization_code, context=None):
        gs_pool = self.pool['google.service']
        all_token = gs_pool._get_google_token_json(cr, uid, authorization_code, self.STR_SERVICE, context=context)

        vals = {}
        vals['google_%s_rtoken' % self.STR_SERVICE] = all_token.get('refresh_token')
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')

        # write in ICP
        print all_token
        
        icp = self.pool['ir.config_parameter']
        # TEMP
        #YOUR_WEBSITE.write(cr, SUPERUSER_ID, uid, vals, context=context)

        icp.set_param(cr, SUPERUSER_ID, 'google_%s_rtoken' % self.STR_SERVICE, all_token.get('refresh_token'))
        icp.set_param(cr, SUPERUSER_ID, 'google_%s_token_validity' % self.STR_SERVICE, datetime.now() + timedelta(seconds=all_token.get('expires_in')))
        icp.set_param(cr, SUPERUSER_ID, 'google_%s_token' % self.STR_SERVICE, all_token.get('access_token'))

        # EXAMPLE OF USE AFTER
        xxx = self.get_list_account(cr, uid)
        import pprint; pprint.pprint(xxx)


    


