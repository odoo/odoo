# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.http import request


class UtmMedium(models.Model):
    # OLD crm.case.channel
    _name = 'utm.medium'
    _description = 'Channels'
    _order = 'name'

    name = fields.Char(string='Channel Name', required=True)
    active = fields.Boolean(default=True)


class UtmCampaign(models.Model):
    # OLD crm.case.resource.type
    _name = 'utm.campaign'
    _description = 'Campaign'

    name = fields.Char(string='Campaign Name', required=True, translate=True)


class UtmSource(models.Model):
    _name = 'utm.source'
    _description = 'Source'

    name = fields.Char(string='Source Name', required=True, translate=True)


class UtmMixin(models.AbstractModel):

    """Mixin class for objects which can be tracked by marketing. """
    _name = 'utm.mixin'

    campaign_id = fields.Many2one('utm.campaign', 'Campaign',
                                  help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', 'Source',
                                help="This is the source of the link Ex:Search Engine, another domain,or name of email list")
    medium_id = fields.Many2one('utm.medium', 'Medium',
                                help="This is the method of delivery.Ex: Postcard, Email, or Banner Ad", oldname='channel_id')

    def tracking_fields(self):
        return [
            # ("URL_PARAMETER", "FIELD_NAME_MIXIN", "NAME_IN_COOKIES")
            ('utm_campaign', 'campaign_id', 'odoo_utm_campaign'),
            ('utm_source', 'source_id', 'odoo_utm_source'),
            ('utm_medium', 'medium_id', 'odoo_utm_medium'),
        ]

    @api.model
    def default_get(self, fields):
        values = super(UtmMixin, self).default_get(fields)

        for url_param, field_name, cookie_name in self.tracking_fields():
            if field_name in fields:
                field = self._fields[field_name]
                value = False
                if request:
                    # ir_http dispatch saves the url params in a cookie
                    value = request.httprequest.cookies.get(cookie_name)
                # if we receive a string for a many2one, we search/create the id
                if field.type == 'many2one' and isinstance(value, basestring) and value:
                    Model = self.env[field.comodel_name]
                    records = Model.search([('name', '=', value)], limit=1)
                    if not records:
                        records = Model.create({'name': value})
                    value = records.id
                values[field_name] = value
        return values
