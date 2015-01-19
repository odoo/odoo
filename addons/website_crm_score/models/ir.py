# -*- coding: utf-8 -*-
from openerp import fields, models
from openerp.http import request
from openerp.osv import osv


class ir_http(models.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        response = super(ir_http, self)._dispatch()

        if getattr(response, 'status_code', 0) == 200:
            if request.endpoint and request.endpoint.routing and request.endpoint.routing.get('track'):
                lead_id = request.env["crm.lead"].decode(request)
                url = request.httprequest.url
                vals = {'lead_id': lead_id, 'user_id': request.session.get('uid'), 'url': url}
                if not lead_id or request.env['website.crm.pageview'].create_pageview(vals):
                    # create_pageview was fail
                    response.delete_cookie('lead_id')
                    request.session.setdefault('pages_viewed', {})[url] = fields.Datetime.now()
                    request.session.modified = True

        return response


class view(osv.osv):
    _inherit = "ir.ui.view"

    track = fields.Boolean(string='Track', default=False, help="Allow to specify for one page of the website to be trackable or not")
