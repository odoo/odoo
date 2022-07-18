# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from werkzeug.urls import url_join

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import url_for
from odoo.addons.website.tools import text_from_html
from odoo.http import request
from odoo.osv import expression
from odoo.exceptions import AccessError
from odoo.tools import escape_psql
from odoo.tools.json import scriptsafe as json_safe

logger = logging.getLogger(__name__)


class SeoMetadata(models.AbstractModel):

    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    is_seo_optimized = fields.Boolean("SEO optimized", compute='_compute_is_seo_optimized')
    website_meta_title = fields.Char("Website meta title", translate=True)
    website_meta_description = fields.Text("Website meta description", translate=True)
    website_meta_keywords = fields.Char("Website meta keywords", translate=True)
    website_meta_og_img = fields.Char("Website opengraph image")
    seo_name = fields.Char("Seo name", translate=True)

    def _compute_is_seo_optimized(self):
        for record in self:
            record.is_seo_optimized = record.website_meta_title and record.website_meta_description and record.website_meta_keywords

    def _default_website_meta(self):
        """ This method will return default meta information. It return the dict
            contains meta property as a key and meta content as a value.
            e.g. 'og:type': 'website'.

            Override this method in case you want to change default value
            from any model. e.g. change value of og:image to product specific
            images instead of default images
        """
        self.ensure_one()
        company = request.website.company_id.sudo()
        title = (request.website or company).name
        if 'name' in self:
            title = '%s | %s' % (self.name, title)

        img_field = 'social_default_image' if request.website.has_social_default_image else 'logo'

        # Default meta for OpenGraph
        default_opengraph = {
            'og:type': 'website',
            'og:title': title,
            'og:site_name': company.name,
            'og:url': url_join(request.httprequest.url_root, url_for(request.httprequest.path)),
            'og:image': request.website.image_url(request.website, img_field),
        }
        # Default meta for Twitter
        default_twitter = {
            'twitter:card': 'summary_large_image',
            'twitter:title': title,
            'twitter:image': request.website.image_url(request.website, img_field, size='300x300'),
        }
        if company.social_twitter:
            default_twitter['twitter:site'] = "@%s" % company.social_twitter.split('/')[-1]

        return {
            'default_opengraph': default_opengraph,
            'default_twitter': default_twitter
        }

    def get_website_meta(self):
        """ This method will return final meta information. It will replace
            default values with user's custom value (if user modified it from
            the seo popup of frontend)

            This method is not meant for overridden. To customize meta values
            override `_default_website_meta` method instead of this method. This
            method only replaces user custom values in defaults.
        """
        root_url = request.httprequest.url_root.strip('/')
        default_meta = self._default_website_meta()
        opengraph_meta, twitter_meta = default_meta['default_opengraph'], default_meta['default_twitter']
        if self.website_meta_title:
            opengraph_meta['og:title'] = self.website_meta_title
            twitter_meta['twitter:title'] = self.website_meta_title
        if self.website_meta_description:
            opengraph_meta['og:description'] = self.website_meta_description
            twitter_meta['twitter:description'] = self.website_meta_description
        opengraph_meta['og:image'] = url_join(root_url, url_for(self.website_meta_og_img or opengraph_meta['og:image']))
        twitter_meta['twitter:image'] = url_join(root_url, url_for(self.website_meta_og_img or twitter_meta['twitter:image']))
        return {
            'opengraph_meta': opengraph_meta,
            'twitter_meta': twitter_meta,
            'meta_description': default_meta.get('default_meta_description')
        }


class WebsiteCoverPropertiesMixin(models.AbstractModel):

    _name = 'website.cover_properties.mixin'
    _description = 'Cover Properties Website Mixin'

    cover_properties = fields.Text('Cover Properties', default=lambda s: json_safe.dumps(s._default_cover_properties()))

    def _default_cover_properties(self):
        return {
            "background_color_class": "o_cc3",
            "background-image": "none",
            "opacity": "0.2",
            "resize_class": "o_half_screen_height",
        }

    def _get_background(self, height=None, width=None):
        self.ensure_one()
        properties = json_safe.loads(self.cover_properties)
        img = properties.get('background-image', "none")

        if img.startswith('url(/web/image/'):
            suffix = ""
            if height is not None:
                suffix += "&height=%s" % height
            if width is not None:
                suffix += "&width=%s" % width
            if suffix:
                suffix = '?' not in img and "?%s" % suffix or suffix
                img = img[:-1] + suffix + ')'
        return img

    def write(self, vals):
        if 'cover_properties' not in vals:
            return super().write(vals)

        cover_properties = json_safe.loads(vals['cover_properties'])
        resize_classes = cover_properties.get('resize_class', '').split()
        classes = ['o_half_screen_height', 'o_full_screen_height', 'cover_auto']
        if not set(resize_classes).isdisjoint(classes):
            # Updating cover properties and the given 'resize_class' set is
            # valid, normal write.
            return super().write(vals)

        # If we do not receive a valid resize_class via the cover_properties, we
        # keep the original one (prevents updates on list displays from
        # destroying resize_class).
        copy_vals = dict(vals)
        for item in self:
            old_cover_properties = json_safe.loads(item.cover_properties)
            cover_properties['resize_class'] = old_cover_properties.get('resize_class', classes[0])
            copy_vals['cover_properties'] = json_safe.dumps(cover_properties)
            super(WebsiteCoverPropertiesMixin, item).write(copy_vals)
        return True


class WebsiteMultiMixin(models.AbstractModel):

    _name = 'website.multi.mixin'
    _description = 'Multi Website Mixin'

    website_id = fields.Many2one(
        "website",
        string="Website",
        ondelete="restrict",
        help="Restrict publishing to this website.",
        index=True,
    )

    def can_access_from_current_website(self, website_id=False):
        can_access = True
        for record in self:
            if (website_id or record.website_id.id) not in (False, request.env['website'].get_current_website().id):
                can_access = False
                continue
        return can_access


class WebsitePublishedMixin(models.AbstractModel):

    _name = "website.published.mixin"
    _description = 'Website Published Mixin'

    website_published = fields.Boolean('Visible on current website', related='is_published', readonly=False)
    is_published = fields.Boolean('Is Published', copy=False, default=lambda self: self._default_is_published(), index=True)
    can_publish = fields.Boolean('Can Publish', compute='_compute_can_publish')
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    @api.depends_context('lang')
    def _compute_website_url(self):
        for record in self:
            record.website_url = '#'

    def _default_is_published(self):
        return False

    def website_publish_button(self):
        self.ensure_one()
        return self.write({'website_published': not self.website_published})

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super(WebsitePublishedMixin, self).create(vals_list)
        is_publish_modified = any(
            [set(v.keys()) & {'is_published', 'website_published'} for v in vals_list]
        )
        if is_publish_modified and any(not record.can_publish for record in records):
            raise AccessError(self._get_can_publish_error_message())

        return records

    def write(self, values):
        if 'is_published' in values and any(not record.can_publish for record in self):
            raise AccessError(self._get_can_publish_error_message())

        return super(WebsitePublishedMixin, self).write(values)

    def create_and_get_website_url(self, **kwargs):
        return self.create(kwargs).website_url

    def _compute_can_publish(self):
        """ This method can be overridden if you need more complex rights management than just 'website_publisher'
        The publish widget will be hidden and the user won't be able to change the 'website_published' value
        if this method sets can_publish False """
        for record in self:
            record.can_publish = True

    @api.model
    def _get_can_publish_error_message(self):
        """ Override this method to customize the error message shown when the user doesn't
        have the rights to publish/unpublish. """
        return _("You do not have the rights to publish/unpublish")


class WebsitePublishedMultiMixin(WebsitePublishedMixin):

    _name = 'website.published.multi.mixin'
    _inherit = ['website.published.mixin', 'website.multi.mixin']
    _description = 'Multi Website Published Mixin'

    website_published = fields.Boolean(compute='_compute_website_published',
                                       inverse='_inverse_website_published',
                                       search='_search_website_published',
                                       related=False, readonly=False)

    @api.depends('is_published', 'website_id')
    @api.depends_context('website_id')
    def _compute_website_published(self):
        current_website_id = self._context.get('website_id')
        for record in self:
            if current_website_id:
                record.website_published = record.is_published and (not record.website_id or record.website_id.id == current_website_id)
            else:
                record.website_published = record.is_published

    def _inverse_website_published(self):
        for record in self:
            record.is_published = record.website_published

    def _search_website_published(self, operator, value):
        if not isinstance(value, bool) or operator not in ('=', '!='):
            logger.warning('unsupported search on website_published: %s, %s', operator, value)
            return [()]

        if operator in expression.NEGATIVE_TERM_OPERATORS:
            value = not value

        current_website_id = self._context.get('website_id')
        is_published = [('is_published', '=', value)]
        if current_website_id:
            on_current_website = self.env['website'].website_domain(current_website_id)
            return (['!'] if value is False else []) + expression.AND([is_published, on_current_website])
        else:  # should be in the backend, return things that are published anywhere
            return is_published

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': url_join(self.website_id._get_http_domain(), self.website_url) if self.website_id else self.website_url,
            'target': 'self',
        }


class WebsiteSearchableMixin(models.AbstractModel):
    """Mixin to be inherited by all models that need to searchable through website"""
    _name = 'website.searchable.mixin'
    _description = 'Website Searchable Mixin'

    @api.model
    def _search_build_domain(self, domain_list, search, fields, extra=None):
        """
        Builds a search domain AND-combining a base domain with partial matches of each term in
        the search expression in any of the fields.

        :param domain_list: base domain list combined in the search expression
        :param search: search expression string
        :param fields: list of field names to match the terms of the search expression with
        :param extra: function that returns an additional subdomain for a search term

        :return: domain limited to the matches of the search expression
        """
        domains = domain_list.copy()
        if search:
            for search_term in search.split(' '):
                subdomains = [[(field, 'ilike', escape_psql(search_term))] for field in fields]
                if extra:
                    subdomains.append(extra(self.env, search_term))
                domains.append(expression.OR(subdomains))
        return expression.AND(domains)

    @api.model
    def _search_get_detail(self, website, order, options):
        """
        Returns indications on how to perform the searches

        :param website: website within which the search is done
        :param order: order in which the results are to be returned
        :param options: search options

        :return: search detail as expected in elements of the result of website._search_get_details()
            These elements contain the following fields:
            - model: name of the searched model
            - base_domain: list of domains within which to perform the search
            - search_fields: fields within which the search term must be found
            - fetch_fields: fields from which data must be fetched
            - mapping: mapping from the results towards the structure used in rendering templates.
                The mapping is a dict that associates the rendering name of each field
                to a dict containing the 'name' of the field in the results list and the 'type'
                that must be used for rendering the value
            - icon: name of the icon to use if there is no image

        This method must be implemented by all models that inherit this mixin.
        """
        raise NotImplementedError()

    @api.model
    def _search_fetch(self, search_detail, search, limit, order):
        fields = search_detail['search_fields']
        base_domain = search_detail['base_domain']
        domain = self._search_build_domain(base_domain, search, fields, search_detail.get('search_extra'))
        model = self.sudo() if search_detail.get('requires_sudo') else self
        results = model.search(
            domain,
            limit=limit,
            order=search_detail.get('order', order)
        )
        count = model.search_count(domain)
        return results, count

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = self.read(fetch_fields)[:limit]
        for result in results_data:
            result['_fa'] = icon
            result['_mapping'] = mapping
        html_fields = [config['name'] for config in mapping.values() if config.get('html')]
        if html_fields:
            for result, data in zip(self, results_data):
                for html_field in html_fields:
                    if data[html_field]:
                        text = text_from_html(data[html_field])
                        text = re.sub('\\s+', ' ', text).strip()
                        data[html_field] = text
        return results_data
