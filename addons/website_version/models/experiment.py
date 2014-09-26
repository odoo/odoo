# -*- coding: utf-8 -*-
from openerp.exceptions import Warning

from openerp.osv import osv, fields
import simplejson

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
        'experiment_id': fields.many2one('website_version.experiment',string="Experiment_id",required=True),
        'frequency': fields.selection([('10','Rare'),('50','Sometimes'),('100','Offen')], 'Frequency'),
        'google_index': fields.function(_get_index,type='integer', string='Google_index'),
    }

    _defaults = {
        'frequency': '10',
    }

EXPERIMENT_STATES = [('draft','Draft'),('running','Running'),('done','Done')]
class Experiment(osv.Model):
    _name = "website_version.experiment"
    _inherit = ['mail.thread']

    def create(self, cr, uid, vals, context=None):
        print vals
        # exp={}
        # exp['name'] = vals['name']
        # exp['state'] = vals['state']
        # exp['variations'] =[]
        # exp['variations'].append({'name':'master'})
        # l =  vals.get('experiment_snapshot_ids')
        # for snap in l:
        #     name = self.pool['website_version.snapshot'].browse(cr, uid, [snap[2]['snapshot_id']],context)[0].name
        #     exp['variations'].append({'name':name})
        # google_id = self.pool['google.management'].create_an_experiment(cr, uid, exp, context=context)
        # if not google_id:
        #     raise Warning("Please askhkjgjk to check api ...")
        # vals['google_id'] = google_id
        return super(Experiment, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        print vals
        name = vals.get('name')
        state = vals.get('state')
        exp_snaps = vals.get('experiment_snapshot_ids')
        for exp in self.browse(cr, uid, ids, context=context):
            temp={}
            if name:
                temp['name'] = name
            else:
                temp['name'] = exp.name
            if state:
                temp['state'] = state
            else:
                temp['state'] = exp.state
            if exp_snaps:
                index = 0
                temp['variations'] = ['master']
                for exp_s in exp.experiment_snapshot_ids:
                    if not exp_snaps[index][0] == 2:
                        temp['variations'].append(exp_s.snapshot_id.name)
                    index+=1
                while index< len(exp_snaps):
                    snap_id = exp_snaps[index][2]['snapshot_id']
                    snap_name = self.pool['website_version.snapshot'].browse(cr, uid, [snap_id], context=context)[0].name
                    temp['variations'].append(snap_name)
                    index+=1
            else:
                temp['variations'] = ['master']
                for exp_s in exp.experiment_snapshot_ids:
                    temp['variations'].append(exp_s.snapshot_id.name)

            print temp
            #self.pool['google.management'].update_an_experiment(self, cr, uid, temp, exp.google_id, context=None)
        return super(Experiment, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        print ids
        # from pudb import set_trace; set_trace()
        # for exp in self.browse(cr, uid, ids, context=context):
        #    self.pool['google.management'].delete_an_experiment(self, cr, uid, exp.google_id, context=context)
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
        # 'state': _get_state
        'state': lambda *args, **kwargs : ([s[0] for s in EXPERIMENT_STATES], dict()),
    }

class google_management(osv.AbstractModel):
    STR_SERVICE = 'management'
    _name = 'google.%s' % STR_SERVICE

    def generate_data(self, cr, uid, experiment, isCreating=False, context=None):
        
        data = {
            'name': experiment['name'],
            'status': experiment['state'],
            'variations': experiment['variations']
        }

        return data

    def create_an_experiment(self, cr, uid, experiment, context=None):
        gs_pool = self.pool['google.service']
        data = self.generate_data(cr, uid, experiment, isCreating=True, context=context)

        accountId='55031254'
        webPropertyId='UA-55031254-1'
        profileId='1'

        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments?key=AIzaSyB2MIVlaewGk1sPG_UKtLlv4g-LOAzXh-Q' % (accountId, webPropertyId, profileId)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)

        try:
            x = gs_pool._do_request(cr, uid, url, data_json, headers, type='POST', context=context)
        except:
            x = False
        return x

    def update_an_experiment(self, cr, uid, experiment, experiment_id, context=None):
        gs_pool = self.pool['google.service']
        data = self.generate_data(cr, uid, experiment, isCreating=True, context=context)

        accountId='55031254'
        webPropertyId='UA-55031254-1'
        profileId='1'

        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' % (accountId, webPropertyId, profileId,experiment_id)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)

        return gs_pool._do_request(cr, uid, url, data_json, headers, type='PUT', context=context)

    def delete_an_experiment(self, cr, uid, experiment_id, context=None):
        gs_pool = self.pool['google.service']

        accountId='55031254'
        webPropertyId='UA-55031254-1'
        profileId='1'
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' %(accountId, webPropertyId, profileId,experiment_id)

        return gs_pool._do_request(cr, uid, url, params, headers, type='DELETE', context=context)


