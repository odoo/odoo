# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.website.tools import text_from_html


class EventBoothCategory(models.Model):
    _name = 'event.booth.category'
    _inherit = ['event.booth.category', 'website.structured_data.mixin']

    def _prepare_jsonld_vals(self):
        self.ensure_one()
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        vals = {
            '@type': 'Product',
            'name': self.name,
        }
        if description := (self.description and text_from_html(self.description, True)):
            vals['description'] = description
        if self.image_1920:
            image_url = self.env['website'].image_url(self, 'image_1920', size=1024)
            vals['image'] = f'{website.get_base_url()}{image_url}'
        return vals

    def _get_breadcrumb_items(self, is_detail_page=False):
        event = self.env['event.event'].browse(self.env.context.get('event_id'))
        if not event:
            return super()._get_breadcrumb_items(is_detail_page)
        items = event._get_breadcrumb_items(True)
        items.append((self.env._("Become exhibitor"), f'{event.website_url}/booth'))
        return items

    def _get_jsonld_dict(self, is_detail_page=False):
        schemas = super()._get_jsonld_dict(is_detail_page)
        # The listing the visitor is on is the last breadcrumb item, which is
        # only there once the event is known.
        items = self._get_breadcrumb_items()
        if self and len(items) > 1:
            name, path = items[-1]
            schemas.append(self._build_collectionpage_jsonld_vals(
                name, path, self, embed_items=True,
            ))
        return schemas
