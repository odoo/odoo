# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.http import request


class UtmMixin(models.AbstractModel):
    """ Mixin class for objects which can be tracked by marketing. """
    _name = 'utm.mixin'
    _description = 'UTM Mixin'

    campaign_id = fields.Many2one('utm.campaign', 'Campaign',
                                  help="This is a name that helps you keep track of your different campaign efforts, e.g. Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', 'Source',
                                help="This is the source of the link, e.g. Search Engine, another domain, or name of email list")
    medium_id = fields.Many2one('utm.medium', 'Medium',
                                help="This is the method of delivery, e.g. Postcard, Email, or Banner Ad", oldname='channel_id')

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            values.update(self._get_missing_utm_values(values, force_create=True))
        return super(UtmMixin, self).create(values_list)

    @api.model
    def default_get(self, fields):
        values = super(UtmMixin, self).default_get(fields)

        # We ignore UTM for salemen, except some requests that could be done as superuser_id to bypass access rights.
        if not self.env.is_superuser() and self.env.user.has_group('sales_team.group_sale_salesman'):
            return values

        values.update(self._get_missing_utm_values(values))
        return values

    def _get_missing_utm_values(self, values, force_create=False):
        # Create from cookies if needed
        utm_values = {}

        for url_param, field_name, cookie_name in self.env['utm.mixin'].tracking_fields():
            field = self._fields.get(field_name)
            if field and 'default_%s' % field_name not in self._context and not values.get(field_name):
                value = False
                if request:
                    # ir_http dispatch saves the url params in a cookie
                    value = request.httprequest.cookies.get(cookie_name)
                # if we receive a string for a many2one, we search/create the id
                if field.type == 'many2one' and isinstance(value, str) and value:
                    Model = self.env[field.comodel_name]
                    record = Model.search([('name', '=', value)], limit=1)
                    if record:
                        utm_values[field_name] = record.id
                    elif force_create:
                        utm_values[field_name] = Model.create({'name': value}).id
        return utm_values

    def tracking_fields(self):
        # This function cannot be overridden in a model which inherit utm.mixin
        # Limitation by the heritage on AbstractModel
        # record_crm_lead.tracking_fields() will call tracking_fields() from module utm.mixin (if not overridden on crm.lead)
        # instead of the overridden method from utm.mixin.
        # To force the call of overridden method, we use self.env['utm.mixin'].tracking_fields() which respects overridden
        # methods of utm.mixin, but will ignore overridden method on crm.lead
        return [
            # ("URL_PARAMETER", "FIELD_NAME_MIXIN", "NAME_IN_COOKIES")
            ('utm_campaign', 'campaign_id', 'odoo_utm_campaign'),
            ('utm_source', 'source_id', 'odoo_utm_source'),
            ('utm_medium', 'medium_id', 'odoo_utm_medium'),
        ]
