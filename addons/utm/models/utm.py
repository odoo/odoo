# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields
from openerp.http import request


class utm_medium(osv.Model):
    # OLD crm.case.channel
    _name = "utm.medium"
    _description = "Channels"
    _order = 'name'
    _columns = {
        'name': fields.char('Channel Name', required=True),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: 1,
    }


class utm_campaign(osv.Model):
    # OLD crm.case.resource.type
    _name = "utm.campaign"
    _description = "Campaign"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Campaign Name', required=True, translate=True),
    }


class utm_source(osv.Model):
    _name = "utm.source"
    _description = "Source"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Source Name', required=True, translate=True),
    }


class utm_mixin(osv.AbstractModel):
    """Mixin class for objects which can be tracked by marketing. """
    _name = 'utm.mixin'

    _columns = {
        'campaign_id': fields.many2one('utm.campaign', 'Campaign',  # old domain ="['|',('team_id','=',team_id),('team_id','=',False)]"
                                       help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, Christmas_Special"),
        'source_id': fields.many2one('utm.source', 'Source', help="This is the source of the link Ex: Search Engine, another domain, or name of email list"),
        'medium_id': fields.many2one('utm.medium', 'Medium', help="This is the method of delivery. Ex: Postcard, Email, or Banner Ad", oldname='channel_id'),
    }

    def tracking_fields(self):
        # This function cannot be overridden in a model which inherit utm.mixin
        # Limitation by the heritage on AbstractModel
        # record_crm_lead.tracking_fields() will call tracking_fields() from module utm.mixin (if not overridden on crm.lead)
        # instead of the overridden method from utm.mixin.
        # To force the call of overridden method, we use self.pool['utm.mixin'].tracking_fields() which respects overridden
        # methods of utm.mixin, but will ignore overridden method on crm.lead
        return [
            # ("URL_PARAMETER", "FIELD_NAME_MIXIN", "NAME_IN_COOKIES")
            ('utm_campaign', 'campaign_id', 'odoo_utm_campaign'),
            ('utm_source', 'source_id', 'odoo_utm_source'),
            ('utm_medium', 'medium_id', 'odoo_utm_medium')
        ]

    def tracking_get_values(self, cr, uid, vals, context=None):
        for key, fname, cook in self.pool['utm.mixin'].tracking_fields():
            field = self._fields[fname]
            value = vals.get(fname) or (request and request.httprequest.cookies.get(cook))  # params.get should be always in session by the dispatch from ir_http
            if field.type == 'many2one' and isinstance(value, basestring):
                # if we receive a string for a many2one, we search/create the id
                if value:
                    Model = self.pool[field.comodel_name]
                    rel_id = Model.name_search(cr, uid, value, context=context)
                    if rel_id:
                        rel_id = rel_id[0][0]
                    else:
                        rel_id = Model.create(cr, uid, {'name': value}, context=context)
                vals[fname] = rel_id
            else:
                # Here the code for others cases that many2one
                vals[fname] = value
        return vals

    def _get_default_track(self, cr, uid, field, context=None):
        return self.tracking_get_values(cr, uid, {}, context=context).get(field)

    _defaults = {
        'source_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'source_id', ctx),
        'campaign_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'campaign_id', ctx),
        'medium_id': lambda self, cr, uid, ctx: self._get_default_track(cr, uid, 'medium_id', ctx),
    }
