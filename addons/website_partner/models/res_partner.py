# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata']

    website_description = fields.Html('Website Partner Full Description', strip_style=True, sanitize_overridable=True, translate=html_translate)
    website_short_description = fields.Text('Website Partner Short Description', translate=True)
    is_published = fields.Boolean(tracking=True)

    def _compute_website_url(self):
        super()._compute_website_url()
        for partner in self:
            if partner.id:
                partner.website_url = "/partners/%s" % self.env['ir.http']._slug(partner)

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'is_published' in init_values:
            if self.is_published:
                return self.env.ref('website_partner.mt_partner_published', raise_if_not_found=False)
            return self.env.ref('website_partner.mt_partner_unpublished', raise_if_not_found=False)
        return super()._track_subtype(init_values)
