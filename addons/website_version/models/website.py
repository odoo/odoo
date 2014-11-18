# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
from openerp.http import request
import random
import json


class NewWebsite(osv.Model):
    _inherit = "website"

    _columns = {
        'tuto_sync': fields.boolean("How to get GA key and View ID"),
        'google_analytics_view_id': fields.char('View ID'),
        'google_management_authorization': fields.char('Google authorization')
    }

    def get_current_version(self,cr,uid,context=None):
        snap = request.registry['website_version.version']
        version_id=request.context.get('version_id')

        if not version_id:
            request.context['version_id'] = 0
            return (0, '')
        return snap.name_get(cr, uid, [version_id], context=context)[0];

    def get_current_website(self, cr, uid, context=None):

        website = super(NewWebsite,self).get_current_website(cr, uid, context=context) 

        exp_ids = self.pool["website_version.experiment"].search(cr, uid, [('state','=','running'),('website_id.id','=',website.id)], context=context)
        exps = self.pool["website_version.experiment"].browse(cr, uid, exp_ids, context=context)
        if not 'website_version_experiment' in request.httprequest.cookies:
            EXP = request.context.get('website_version_experiment', {})
        else:
            EXP = json.loads(request.httprequest.cookies.get('website_version_experiment'))
        for exp in exps:
            if not str(exp.google_id) in EXP:
                result=[]
                pond_sum=0
                for exp_snap in exp.experiment_version_ids:
                    result.append([int(exp_snap.frequency)+pond_sum, exp_snap.version_id.id])
                    pond_sum+=int(exp_snap.frequency)
                if pond_sum:
                    #by default master has a frequency of 50
                    pond_sum = pond_sum + 50
                    #by default on master
                    #We set the google_id as key in the cookie to avoid problem when reinitializating the db
                    EXP[str(exp.google_id)] = str(0)
                x = random.getrandbits(128)%pond_sum
                for res in result:
                    if x<res[0]:
                        EXP[str(exp.google_id)] = str(res[1])
                        break
        request.context['website_version_experiment'] = EXP
     

        request.context['website_id'] = website.id

        if 'version_id' in request.session:
            request.context['version_id'] = request.session.get('version_id')
        elif self.pool['res.users'].has_group(cr, uid, 'base.group_website_publisher'):
            request.context['version_id'] = 0
        else:
            request.context['experiment_id'] = 1
        return website

    def save_ab_config(self,cr,uid,ids,context=None):
        website_id = context.get('active_id')
        google_analytics_key = context.get('google_analytics_key')
        google_analytics_view_id = context.get('google_analytics_view_id')
        self.write(cr, uid, [website_id], {'google_analytics_key':google_analytics_key, 'google_analytics_view_id':google_analytics_view_id}, context=context)



