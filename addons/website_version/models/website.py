# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
import werkzeug.wrappers
from openerp.http import request, Response
import random
import json


class NewWebsite(osv.Model):
    _inherit = "website"

    def get_current_snapshot(self,cr,uid,context=None):
        snap = request.registry['website_version.snapshot']
        snapshot_id=request.context.get('snapshot_id')
        experiment_id=request.context.get('experiment_id')
        if experiment_id:
            return (0, 'experiment')

        if not snapshot_id:
            request.context['snapshot_id'] = 0
            return (0, 'master')
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
                    result.append([exp_snap.ponderation+pond_sum, exp_snap.snapshot_id.id])
                    pond_sum+=exp_snap.ponderation
                if pond_sum:
                    #RANDOM
                    x = random.getrandbits(128)%pond_sum
                    for res in result:
                        if x<res[0]:
                            EXP[str(exp.id)] = str(res[1])
                            break
        request.context['EXP'] = EXP
     

        request.context['website_id'] = website.id

        if request.session.get('snapshot_id'):
            request.context['snapshot_id'] = request.session.get('snapshot_id')
        elif request.session.get('master'):
            request.context['snapshot_id'] = 0
        else:
            request.context['experiment_id'] = 1        

        return website


