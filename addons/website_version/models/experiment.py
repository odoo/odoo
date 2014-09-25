# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
import simplejson

class Experiment_snapshot(osv.Model):
    _name = "website_version.experiment_snapshot"
    
    _columns = {
        'snapshot_id': fields.many2one('website_version.snapshot',string="Snapshot_id",required=True ,ondelete='cascade'),
        'experiment_id': fields.many2one('website_version.experiment',string="Experiment_id",required=True),
        'frequency': fields.selection([('10','Rare'),('50','Sometimes'),('100','Offen')], 'Frequency'),
    }

    _defaults = {
        'frequency': '10',
    }

EXPERIMENT_STATES = [('draft','Draft'),('running','Running'),('done','Done')]
class Experiment(osv.Model):
    _name = "website_version.experiment"
    _inherit = ['mail.thread']


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

    # def _get_state(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
    #     from pudb import set_trace; set_trace()
    #     return STATES, {}
    
    _columns = {
        'name': fields.char(string="Title", size=256, required=True),
        'experiment_snapshot_ids': fields.one2many('website_version.experiment_snapshot', 'experiment_id',string="experiment_snapshot_ids"),
        'website_id': fields.many2one('website',string="Website", required=True),
        'state': fields.selection(EXPERIMENT_STATES, 'Status', required=True, copy=False, track_visibility='onchange'),
        'color': fields.integer('Color Index'),
        'version_number' : fields.function(_get_version_number,type='integer'),
        'sequence': fields.integer('Sequence', required=True, help="Test."),
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
        # 'state': _get_state
        'state': lambda *args, **kwargs : ([s[0] for s in EXPERIMENT_STATES], dict()),
    }

class google_management(osv.AbstractModel):
    STR_SERVICE = 'management'
    _name = 'google.%s' % STR_SERVICE

    def generate_data(self, cr, uid, experiment, isCreating=False, context=None):
        accountId='55031254',
        webPropertyId='UA-55031254-1',
        profileId='1',
        
        data = {
            'name': experiment.name,
            'status': experiment.status,
            'variations': experiment.variontions
        }

        return data

    def create_an_experiment(self, cr, uid, experiment, context=None):
        gs_pool = self.pool['google.service']
        data = self.generate_data(cr, uid, experiment, isCreating=True, context=context)

        accountId='55031254',
        webPropertyId='UA-55031254-1',
        profileId='1'

        url = 'analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments' % (accountId, webPropertyId, profileId)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)

        return gs_pool._do_request(cr, uid, url, data_json, headers, type='POST', context=context)

    def update_an_experiment(self, cr, uid, experiment, context=None):
        gs_pool = self.pool['google.service']
        data = self.generate_data(cr, uid, experiment, isCreating=True, context=context)

        accountId='55031254',
        webPropertyId='UA-55031254-1',
        profileId='1'

        url = 'analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' % (accountId, webPropertyId, profileId,experiment.id)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)

        return gs_pool._do_request(cr, uid, url, data_json, headers, type='PUT', context=context)

    def delete_an_experiment(self, cr, uid, experiment_id, context=None):
        gs_pool = self.pool['google.service']

        accountId='55031254',
        webPropertyId='UA-55031254-1',
        profileId='1'
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = 'analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' %(accountId, webPropertyId, profileId,experiment.id)

        return gs_pool._do_request(cr, uid, url, params, headers, type='DELETE', context=context)


