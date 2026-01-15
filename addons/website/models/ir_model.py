# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import ir_http
from odoo import models


class Base(models.AbstractModel):
    _inherit = 'base'

    def get_base_url(self):
        """
        Returns the base url for a given record, given the following priority:

        1. If the record has a `website_id` field, we use the url from this
           website as base url, if set.
        2. If the record has a `company_id` field, we use the website from that
           company (if set). Note that a company doesn't really have a website,
           it is retrieve through some heuristic in its `website_id`'s compute.
        3. Use the ICP `web.base.url` (super)

        :return: the base url for this record
        :rtype: string
        """
        # Ensure zero or one record
        if not self:
            return super().get_base_url()
        self.ensure_one()

        if self._name == 'website':
            # Note that website_1.company_id.website_id might not be website_1
            return self.domain or super().get_base_url()
        if 'website_id' in self and self.sudo().website_id.domain:
            return self.sudo().website_id.domain
        if 'company_id' in self and self.company_id.website_id.domain:
            return self.company_id.website_id.domain
        return super().get_base_url()

    def get_website_meta(self):
        # dummy version of 'get_website_meta' above; this is a graceful fallback
        # for models that don't inherit from 'website.seo.metadata'
        return {}

    def _get_base_lang(self):
        """ Returns the default language of the website as the base language if the record is bound to it """
        website = ir_http.get_request_website()
        if website:
            return website.default_lang_id.code
        return super()._get_base_lang()
