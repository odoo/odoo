# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
import werkzeug.wrappers
from openerp.http import request, Response
import random
import json


class NewWebsite(osv.Model):
    _inherit = "website"

    _columns = {
        'tuto_sync': fields.boolean("Show tutorial"),
        'google_analytics_view_id': fields.char('View ID'),
        'google_management_authorization': fields.char('Google authorization')
    }

    def get_experiment_number(self,cr,uid,context=None):
        exp_run_ids = request.registry['website_version.experiment'].search(cr, uid, [('website_id','=',context.get('website_id'))], context=context)
        return len(exp_run_ids)

    def get_current_snapshot(self,cr,uid,context=None):
        snap = request.registry['website_version.snapshot']
        snapshot_id=request.context.get('snapshot_id')

        if not snapshot_id:
            request.context['snapshot_id'] = 0
            return (0, '')
        return snap.name_get(cr, uid, [snapshot_id], context=context)[0];

    def get_current_website(self, cr, uid, context=None):

        website = super(NewWebsite,self).get_current_website(cr, uid, context=context) 

        exp_ids = self.pool["website_version.experiment"].search(cr, uid, [('state','=','running'),('website_id.id','=',website.id)], context=context)
        exps = self.pool["website_version.experiment"].browse(cr, uid, exp_ids, context=context)
        if not 'EXP' in request.httprequest.cookies:
            EXP = request.context.get('EXP')
            if not EXP:
                EXP = {}            
        else:
            EXP = json.loads(request.httprequest.cookies.get('EXP'))
        for exp in exps:
            if not str(exp.id) in EXP:
                result=[]
                pond_sum=0
                for exp_snap in exp.experiment_snapshot_ids:
                    result.append([int(exp_snap.frequency)+pond_sum, exp_snap.snapshot_id.id])
                    pond_sum+=int(exp_snap.frequency)
                if pond_sum:
                    #by default master has a frequency of 50
                    pond_sum = pond_sum + 50
                    #by default on master
                    EXP[str(exp.id)] = str(0)
                x = random.getrandbits(128)%pond_sum
                for res in result:
                    if x<res[0]:
                        EXP[str(exp.id)] = str(res[1])
                        break
            #else:
                #Check if all versions in running experiments are still there. If not, redirect to master.
        request.context['EXP'] = EXP
     

        request.context['website_id'] = website.id

        if request.session.get('snapshot_id'):
            request.context['snapshot_id'] = request.session.get('snapshot_id')
        elif request.session.get('master') or self.pool['res.users'].has_group(cr, uid, 'base.group_website_publisher'):
            request.context['snapshot_id'] = 0
        else:
            request.context['experiment_id'] = 1
        return website



