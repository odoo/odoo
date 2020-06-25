# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tools.translate import html_translate


class EventSponsor(models.Model):
    _name = 'event.sponsor'
    _inherit = [
        'event.sponsor',
        'website.published.mixin'
    ]
    _rec_name = 'name'
    _order = 'sponsor_type_id, sequence'

    # description
    subtitle = fields.Char('Subtitle', help='Catchy marketing sentence for promote')
    website_description = fields.Html(
        'Description', compute='_compute_website_description',
        sanitize_attributes=False, sanitize_form=True, translate=html_translate,
        readonly=False, store=True)

    @api.depends('partner_id')
    def _compute_website_description(self):
        self._synchronize_with_partner('website_description')

    @api.depends('name', 'event_id.name')
    def _compute_website_url(self):
        super(EventSponsor, self)._compute_website_url()
        for sponsor in self:
            if sponsor.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                base_url = sponsor.event_id.get_base_url()
                sponsor.website_url = '%s/event/%s/exhibitor/%s' % (base_url, slug(sponsor.event_id), slug(sponsor))
