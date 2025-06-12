# coding: utf-8
from odoo import api, models
from odoo.http import request


class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _eval_context(self):
        res = super(IrRule, self)._eval_context()

        # We need is_frontend to avoid showing website's company items in backend
        # (that could be different than current company). We can't use
        # `get_current_website(falback=False)` as it could also return a website
        # in backend (if domain set & match)..
        is_frontend = request and getattr(request, 'is_frontend', False)
        Website = self.env['website']
        res['website'] = is_frontend and Website.get_current_website() or Website
        return res

    def _compute_domain_keys(self):
        """ Return the list of context keys to use for caching ``_compute_domain``. """
        return super(IrRule, self)._compute_domain_keys() + ['website_id']
