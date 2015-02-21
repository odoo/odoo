# -*- coding: utf-8 -*-
import json
from openerp import fields, models, api
from openerp.http import request
import random


class NewWebsite(models.Model):

    _inherit = "website"

    tuto_google_analytics = fields.Boolean("How to get GA key and View ID")
    google_analytics_view_id = fields.Char('View ID')
    google_management_authorization = fields.Char('Google authorization')

    @api.model
    def get_current_version(self, context=None):
        Version = request.env['website_version.version']
        version_id = request.context.get('version_id')

        if not version_id:
            request.context['version_id'] = 0
            return (0, '')
        return (version_id, Version.browse(version_id).name)

    @api.model
    def get_current_website(self):
        website = super(NewWebsite, self).get_current_website()
        #We just set the cookie for the first visit
        if 'website_version_experiment' in request.httprequest.cookies:
            EXP = json.loads(request.httprequest.cookies.get('website_version_experiment'))
        else:
            EXP = request.context.get('website_version_experiment', {})
            exps = self.env["website_version.experiment"].search([('state', '=', 'running'), ('website_id.id', '=', website.id), ('google_id', 'not in', EXP.keys())])
            for exp in exps:
                result = []
                pond_sum = 0
                for exp_snap in exp.experiment_version_ids:
                    result.append([int(exp_snap.frequency)+pond_sum, exp_snap.version_id.id])
                    pond_sum += int(exp_snap.frequency)
                if pond_sum:
                    #by default master has a frequency of 50
                    pond_sum = pond_sum + 50
                    #by default on master
                    #We set the google_id as key in the cookie to avoid problem when reinitializating the db
                    EXP[exp.google_id] = str(0)
                x = random.randint(0, pond_sum-1)
                for res in result:
                    if x < res[0]:
                        EXP[exp.google_id] = str(res[1])
                        break
        request.context['website_version_experiment'] = EXP
        request.context['website_id'] = website.id

        if 'version_id' in request.session:
            request.context['version_id'] = request.session.get('version_id')
        elif self.env['res.users'].has_group('base.group_website_publisher'):
            request.context['version_id'] = 0
        else:
            request.context['experiment_id'] = 1
        return website

    @api.model
    def google_analytics_data(self, main_object):
        #To get the ExpId and the VarId of the view if it is in a running experiment
        result = {}
        if main_object and main_object._name == 'ir.ui.view':
            view = main_object
            #search all the running experiments with the key of view
            exp_ids = self.env['website_version.experiment'].search([('experiment_version_ids.version_id.view_ids.key', '=', view.key), ('state', '=', 'running'), ('experiment_version_ids.version_id.website_id', '=', self.env.context.get('website_id'))])
            if exp_ids:
                #No overlap between running experiments then we can take the first one
                result['expId'] = exp_ids[0].google_id
                version_id = self.env.context.get('version_id') or self.env.context['website_version_experiment'].get(exp_ids[0].google_id)
                if version_id:
                    exp_ver_ids = self.env['website_version.experiment.version'].search([('experiment_id', '=', exp_ids[0].id), ('version_id', '=', int(version_id))], limit=1)
                    if exp_ver_ids:
                        result['expVar'] = exp_ver_ids[0].google_index
                    else:
                        result['expVar'] = 0
        return result


