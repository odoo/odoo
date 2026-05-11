# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons.website.helpers.jsonld_builder import JsonLd
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

    def _build_partner_base_jsonld(self):
        """Build the base partner schema for listing cards."""
        self.ensure_one()
        website = self.env['website'].get_current_website()
        base_url = website.get_base_url()
        schema_type = "LocalBusiness" if self.is_company else "Person"
        schema_data = {
            "@id": f"{base_url}{self.website_url}/#{schema_type}",
            "name": self.display_name,
            "telephone": self.phone,
            "email": self.email,
            "sameAs": f"{base_url}{self.website_url}",
        }
        if self.website:
            schema_data["url"] = self.website
        if self.website_short_description:
            schema_data["description"] = self.website_short_description
        partner_data = JsonLd(schema_type, schema_data)
        if self.country_id:
            nested_schema_data = {
                "address": JsonLd("PostalAddress", {"addressCountry": self.country_id.name}),
            }
            partner_data.add_nested(nested_schema_data)
        if image_url := self.env['website'].image_url(self, 'image_1024'):
            full_image_url = image_url if image_url.startswith('http') else f"{base_url}{image_url}"
            nested_schema_data = {"image": JsonLd("ImageObject", {"url": full_image_url})}
            partner_data.add_nested(nested_schema_data)
        return partner_data

    def _build_partner_jsonld(self):
        """Build the partner schema for partner detail pages."""
        self.ensure_one()
        partner_data = self._build_partner_base_jsonld()
        postal_address = partner_data.get("address")
        schema_data = {
            "streetAddress": self.street,
            "postalCode": self.zip,
            "addressLocality": self.city,
        }
        if self.state_id:
            schema_data["addressRegion"] = self.state_id.name
        postal_address.set(schema_data)
        return partner_data

    def _get_breadcrumb_items(self, is_detail_page=False):
        """Return breadcrumb items for partner listing and detail pages."""
        items = super()._get_breadcrumb_items(is_detail_page)
        items.append((self.env._("Find Resellers"), "/partners"))
        if is_detail_page:
            items.append((self.display_name, self.website_url))
        return items

    def _build_partner_collectionpage_jsonld(self):
        """Build a ``CollectionPage`` schema for the partners listing page."""
        website = self.env['website'].get_current_website()
        base_url = website.get_base_url()
        schema_data = {
            "name": self.env._("Resellers"),
            "url": f"{base_url}/partners",
        }
        item_lists = [
            JsonLd("ListItem", {"position": index + 1}).add_nested({
                "item": partner._build_partner_base_jsonld(),
            }) for index, partner in enumerate(self)
        ]
        main_entity_schema = JsonLd("ItemList").add_nested({
            "itemListElement": item_lists,
        })
        return JsonLd("CollectionPage", schema_data).add_nested({"mainEntity": main_entity_schema})

    def _get_jsonld(self, is_detail_page=False):
        """Return the list of JsonLd schemas for partner page."""
        schemas = super()._get_jsonld(is_detail_page)
        if is_detail_page:
            schemas.append(self._build_partner_jsonld())
            return schemas
        schemas.append(self._build_partner_collectionpage_jsonld())
        return schemas
