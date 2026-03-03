# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


def retrieve_tracked_links_with_urls_and_labels(link_nodes, urls_and_labels, tracking_enabled_status_list):
    """Return the list of links, and the list of urls_and_labes, of which the link tracking is enabled. This will
    filter out links

    Note: the order of the link nodes in `link_nodes` should correspond to the same order in `urls_and_labels`
    as well as to the ones in `tracking_enabled_status_list`.
    I.e. `link_nodes[0]` corresponds to `urls_and_labes[0]` and to `tracking_enabled_status_list[0]`.

    :param list[lxml.etree._Element] link_nodes: The list of the link nodes to process
    :param list[dict] urls_and_labels: The list of the urls mapped to their corresponding labels
    :param list[bool] tracking_enabled_status_list: List of boolean values indicating whether each link has an
    enabled tracking or no. Eg: the tracking status of `link_nodes[0]` is in `tracking_enabled_status_list[0]`.

    :rtype: (list[lxml.etree._Element], list[dict])
    """
    tracked_link_nodes = []
    tracked_urls_and_labels = []
    for node, url_and_label, is_tracking_enabled in zip(link_nodes, urls_and_labels, tracking_enabled_status_list):
        if is_tracking_enabled:
            tracked_link_nodes.append(node)
            tracked_urls_and_labels.append(url_and_label)
    return tracked_link_nodes, tracked_urls_and_labels


def is_link_tracking_enabled(link_node):
    """Check if link tracking is enabled for the given link_node

    :param lxml.etree._Element link_node: The link node of which to check the link tracking status

    :rtype: bool
    """
    prop = link_node.attrib if link_node is not None else None
    if prop and prop.get('data-no-tracking'):
        return prop.get('data-no-tracking') != '1'
    return True


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
        tracking_enabled_status_list = list(map(is_link_tracking_enabled, link_nodes))  # --> [True, False, True, True, ...]
        tracked_link_nodes, tracked_urls_and_labels = retrieve_tracked_links_with_urls_and_labels(link_nodes, urls_and_labels, tracking_enabled_status_list)

        return tracked_link_nodes, tracked_urls_and_labels
