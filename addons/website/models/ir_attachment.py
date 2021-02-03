# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models, api, tools
from odoo.exceptions import UserError
from odoo.tools.translate import _
_logger = logging.getLogger(__name__)


class Attachment(models.Model):

    _inherit = "ir.attachment"

    # related for backward compatibility with saas-6
    website_url = fields.Char(string="Website URL", related='local_url', deprecated=True, readonly=False)
    key = fields.Char(help='Technical field used to resolve multiple attachments in a multi-website environment.')
    website_id = fields.Many2one('website')

    @api.model
    def create(self, vals):
        website = self.env['website'].get_current_website(fallback=False)
        if website and 'website_id' not in vals and 'not_force_website_id' not in self.env.context:
            vals['website_id'] = website.id
        return super(Attachment, self).create(vals)

    @api.model
    def get_serving_groups(self):
        return super(Attachment, self).get_serving_groups() + ['website.group_website_designer']

    @api.model
    def get_serve_attachment(self, url, extra_domain=None, extra_fields=None, order=None):
        website = self.env['website'].get_current_website()
        extra_domain = (extra_domain or []) + website.website_domain()
        order = ('website_id, %s' % order) if order else 'website_id'
        return super(Attachment, self).get_serve_attachment(url, extra_domain, extra_fields, order)

    @api.model
    def get_attachment_by_key(self, key, extra_domain=None, order=None):
        website = self.env['website'].get_current_website()
        extra_domain = (extra_domain or []) + website.website_domain()
        order = ('website_id, %s' % order) if order else 'website_id'
        return super(Attachment, self).get_attachment_by_key(key, extra_domain, order)

    def init(self):
        res = super(Attachment, self).init()
        # ir_http._xmlid_to_obj is using this index for multi-website
        tools.create_index(self._cr, 'ir_attachment_key_website_idx', self._table, ['key', 'website_id'])
        return res
