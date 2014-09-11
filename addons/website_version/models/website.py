# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
import werkzeug.wrappers
from openerp.http import request, Response
import random


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

        if not 'RNG_exp' in request.httprequest.cookies:
            request.context['RNG_exp'] = str(random.getrandbits(128))
        else:
            request.context['RNG_exp'] = request.httprequest.cookies.get('RNG_exp')

        website = super(NewWebsite,self).get_current_website(cr, uid, context=context)      

        request.context['website_id'] = website.id

        if request.session.get('snapshot_id'):
            request.context['snapshot_id'] = request.session.get('snapshot_id')
        elif request.session.get('master'):
            request.context['snapshot_id'] = 0
        else:
            request.context['experiment_id'] = 1        

        return website