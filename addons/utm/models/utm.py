# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.http import request


class UtmMedium(models.Model):
    # OLD crm.case.channel
    _name = 'utm.medium'
    _description = 'Channels'
    _order = 'name'

    name = fields.Char(string='Channel Name', required=True, default=lambda self: self.env['utm.mixin']._get_default_track('medium_id'))
    active = fields.Boolean(string='Active', default=True)


class UtmCampaign(models.Model):
    # OLD crm.case.resource.type
    _name = 'utm.campaign'
    _description = 'Campaign'

    name = fields.Char(string='Campaign Name', required=True, translate=True, default=lambda self: self.env['utm.mixin']._get_default_track('campaign_id'))


class UtmSource(models.Model):
    _name = 'utm.source'
    _description = 'Source'

    name = fields.Char(string='Source Name', required=True, translate=True, default=lambda self: self.env['utm.mixin']._get_default_track('source_id'))


class UtmMixin(models.AbstractModel):

    """Mixin class for objects which can be tracked by marketing. """
    _name = 'utm.mixin'

    def _get_default_track(self, field):
        return self.tracking_get_values({}).get(field)

    campaign_id = fields.Many2one('utm.campaign', 'Campaign',  # old domain ="['|',('team_id','=',team_id),('team_id','=',False)]"
                                  help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', 'Source', help="This is the source of the link Ex:Search Engine, another domain,or name of email list")
    medium_id = fields.Many2one('utm.medium', 'Medium', help="This is the method of delivery.Ex: Postcard, Email, or Banner Ad", oldname='channel_id')

    def tracking_fields(self):
        return [
            # ("URL_PARAMETER", "FIELD_NAME_MIXIN", "NAME_IN_COOKIES")
            ('UtmCampaign', 'campaign_id', 'odoo_utm_campaign'),
            ('UtmSource', 'source_id', 'odoo_utm_source'),
            ('UtmMedium', 'medium_id', 'odoo_utm_medium')]

    @api.model
    def tracking_get_values(self, vals):
        for key, fname, cook in self.tracking_fields():
            field = self._fields[fname]
            value = vals.get(fname) or (request and request.httprequest.cookies.get(cook))  # params.get should be always in session by the dispatch from ir_http
            if field.type == 'many2one' and isinstance(value, basestring):
                # if we receive a string for a many2one, we search/create the id
                if value:
                    Model = self.env[field.comodel_name]
                    rel_id = Model.name_search(value)
                    if rel_id:
                        rel_id = rel_id[0][0]
                    else:
                        rel_id = Model.create({'name': value})
                vals[fname] = rel_id
            else:
                # Here the code for others cases that many2one
                vals[fname] = value
            return vals
