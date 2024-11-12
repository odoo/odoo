from odoo import api, models
from odoo.addons.website.models import ir_http


class IrAccess(models.Model):
    _inherit = 'ir.access'

    @api.model
    def _eval_context(self):
        res = super()._eval_context()

        # We need is_frontend to avoid showing website's company items in backend
        # (that could be different than current company). We can't use
        # `get_current_website(falback=False)` as it could also return a website
        # in backend (if domain set & match)..
        is_frontend = ir_http.get_request_website()
        Website = self.env['website']
        res['website'] = Website.get_current_website() if is_frontend else Website
        return res

    def _get_access_context(self):
        yield from super()._get_access_context()
        yield self.env.context.get('website_id')
