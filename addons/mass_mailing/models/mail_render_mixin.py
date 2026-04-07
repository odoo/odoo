# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    @api.model
    def _render_template_postprocess(self, model, rendered):
        # super will transform relative url to absolute
        rendered = super()._render_template_postprocess(model, rendered)

        # apply shortener after
        if self.env.context.get('post_convert_links'):
            for res_id, html in rendered.items():
                rendered[res_id] = self._shorten_links(
                    html,
                    self.env.context['post_convert_links'],
                    blacklist=['/unsubscribe_from_list', '/view', '/cards']
                )
        return rendered

    def _filter_urls_and_labels(self, link_nodes, urls_and_labels):
        """Return only the links in which link tracking is enabled"""

        def is_link_tracking_enabled(link_node):
            """Check if link tracking is enabled for the given link_node

            :param lxml.etree._Element link_node: The link node of which to check the link tracking status

            :rtype: bool
            """
            prop = link_node.attrib if link_node is not None else None
            if prop and prop.get('data-no-tracking'):
                return prop.get('data-no-tracking') != '1'
            return True

        tracking_enabled_status_list = list(map(is_link_tracking_enabled, link_nodes))  # --> [True, False, True, True, ...]
        tracked_link_nodes = []
        tracked_urls_and_labels = []
        for node, url_and_label, is_tracking_enabled in zip(link_nodes, urls_and_labels, tracking_enabled_status_list):
            if is_tracking_enabled:
                tracked_link_nodes.append(node)
                tracked_urls_and_labels.append(url_and_label)

        return tracked_link_nodes, tracked_urls_and_labels
