# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from html import unescape

import lxml
import markupsafe
from werkzeug import urls

from odoo import api, models, tools
from odoo.addons.link_tracker.tools.html import find_links_with_urls_and_labels
from odoo.tools.mail import is_html_empty, URL_SKIP_PROTOCOL_REGEX, TEXT_URL_REGEX


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    @api.model
    def _shorten_links(self, html, link_tracker_vals, blacklist=None, base_url=None):
        """ Shorten links in an html content. It uses the '/r' short URL routing
        introduced in this module. Using the standard Odoo regex local links are
        found and replaced by global URLs (not including mailto, tel, sms).

        TDE FIXME: could be great to have a record to enable website-based URLs

        :param link_tracker_vals: values given to the created link.tracker, containing
          for example: campaign_id, medium_id, source_id, and any other relevant fields
          like mass_mailing_id in mass_mailing;
        :param list blacklist: list of (local) URLs to not shorten (e.g.
          '/unsubscribe_from_list')
        :param str base_url: either given, either based on config parameter

        :return: updated html
        """
        if not html or is_html_empty(html):
            return html
        base_url = base_url or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        short_schema = base_url + '/r/'

        root_node = lxml.html.fromstring(html)
        link_nodes, urls_and_labels = find_links_with_urls_and_labels(
            root_node, base_url, skip_regex=rf'^{URL_SKIP_PROTOCOL_REGEX}', skip_prefix=short_schema,
            skip_list=blacklist)
        if not link_nodes:
            return html

        links_trackers = self.env['link.tracker'].search_or_create([
            dict(link_tracker_vals, **url_and_label) for url_and_label in urls_and_labels
        ])
        for node, link_tracker in zip(link_nodes, links_trackers):
            node.set("href", link_tracker.short_url)

        new_html = lxml.html.tostring(root_node, encoding="unicode", method="xml")
        if isinstance(html, markupsafe.Markup):
            new_html = markupsafe.Markup(new_html)

        return new_html

    @api.model
    def _shorten_links_text(self, content, link_tracker_vals, blacklist=None, base_url=None):
        """ Shorten links in a string content. Works like ``_shorten_links`` but
        targeting string content, not html.

        :return: updated content
        """
        if not content:
            return content
        base_url = base_url or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        shortened_schema = base_url + '/r/'
        unsubscribe_schema = base_url + '/sms/'
        for original_url in set(re.findall(TEXT_URL_REGEX, content)):
            # don't shorten already-shortened links or links towards unsubscribe page
            if original_url.startswith(shortened_schema) or original_url.startswith(unsubscribe_schema):
                continue
            # support blacklist items in path, like /u/
            parsed = urls.url_parse(original_url, scheme='http')
            if blacklist and any(re.search(item + r'([#?/]|$)', parsed.path) for item in blacklist):
                continue

            create_vals = dict(link_tracker_vals, url=unescape(original_url))
            link = self.env['link.tracker'].search_or_create([create_vals])
            if link.short_url:
                # Ensures we only replace the same link and not a subpart of a longer one, multiple times if applicable
                content = re.sub(re.escape(original_url) + r'(?![\w@:%.+&~#=/-])', link.short_url, content)

        return content
