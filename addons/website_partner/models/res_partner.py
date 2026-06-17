# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata', 'website.structured_data.mixin']

    website_description = fields.Html('Website Partner Full Description', strip_style=True, sanitize_overridable=True, translate=html_translate)
    website_short_description = fields.Text('Website Partner Short Description', translate=True)
    is_published = fields.Boolean(tracking=True)

    def _compute_website_url(self):
        super()._compute_website_url()
        for partner in self:
            if partner.id:
                partner.website_url = "/partners/%s" % self.env['ir.http']._slug(partner)

    def _track_log_get_default_subtype(self, track_init_values):
        self.ensure_one()
        if 'is_published' in track_init_values:
            if self.is_published:
                return self.env.ref('website_partner.mt_partner_published', raise_if_not_found=False) or super()._track_log_get_default_subtype(track_init_values)
            return self.env.ref('website_partner.mt_partner_unpublished', raise_if_not_found=False) or super()._track_log_get_default_subtype(track_init_values)
        return super()._track_log_get_default_subtype(track_init_values)

    def _prepare_jsonld_vals(self):
        self.ensure_one()
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        base_url = website.get_base_url()
        schema_type = 'Organization' if self.is_company else 'Person'
        vals = {
            '@type': schema_type,
            '@id': f'{base_url}{self.website_url}/#{schema_type.lower()}',
            'name': self.display_name,
            'mainEntityOfPage': f'{base_url}{self.website_url}',
        }
        if self.phone:
            vals['telephone'] = self.phone
        if self.email:
            vals['email'] = self.email
        if self.website:
            vals['url'] = self.website
        if self.website_short_description:
            vals['description'] = self.website_short_description
        if address := self._build_postaladdress_jsonld_vals(self):
            vals['address'] = address
        if image_url := self.env['website'].image_url(self, 'image_1024'):
            vals['image'] = f'{base_url}{image_url}'
        return vals

    def _get_breadcrumb_items(self, is_detail_page=False):
        items = super()._get_breadcrumb_items(is_detail_page)
        items.append((self.env._("Find Resellers"), '/partners'))
        if is_detail_page:
            items.append((self.display_name, self.website_url))
        return items

    def _build_profilepage_jsonld_vals(self):
        self.ensure_one()
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        base_url = website.get_base_url()
        return {
            '@type': 'ProfilePage',
            'url': f'{base_url}{self.website_url}',
            'mainEntity': self._prepare_jsonld_vals(),
        }

    def _get_jsonld_dict(self, is_detail_page=False):
        schemas = super()._get_jsonld_dict(is_detail_page)
        if is_detail_page:
            schemas.append(self._build_profilepage_jsonld_vals())
            return schemas
        if self:
            schemas.append(self._build_collectionpage_jsonld_vals(
                self.env._("Resellers"), '/partners', self, name_field='display_name',
            ))
        return schemas
