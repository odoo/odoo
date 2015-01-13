from openerp import fields, models
from openerp.http import request
from openerp.osv import osv


class ir_http(models.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        response = super(ir_http, self)._dispatch()

        if hasattr(response, 'status_code') and response.status_code == 200:  # may not be needed because find_handler not used anymore
            if request.endpoint.routing.get('track', False):
                cr, uid, context = request.cr, request.uid, request.context
                lead_id = request.registry["crm.lead"].decode(request)
                url = request.httprequest.url
                vals = {'lead_id': lead_id, 'partner_id': request.session.get('uid', None), 'url': url}
                if lead_id and request.registry['website.crm.pageview'].create_pageview(cr, uid, vals, context=context):
                    # create_pageview was successful
                    pass
                else:
                    response.delete_cookie('lead_id')
                    request.session.setdefault('pages_viewed', {})[url] = fields.Datetime.now()
                    request.session.modified = True

        return response


class view(osv.osv):
    _inherit = "ir.ui.view"

    track = fields.Boolean(string='Track', default=False, help="Allow to specify for one page of the website to be trackable or not")
