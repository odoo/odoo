

import re

import lxml
from odoo import _, api, models
from odoo.addons.link_tracker.tools.html import find_links_with_urls_and_labels
from odoo.tools.mail import is_html_empty, text_url_replace, URL_SKIP_PROTOCOL_REGEX, TEXT_URL_REGEX


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    @api.depends('body_arch', 'mailing_model_name')
    def _compute_warning_message(self):
        super()._compute_warning_message()
        for mailing in self.filtered(lambda m: m.mailing_model_name == 'hr.employee'):
            # regex search unsubscribe from list; print warning if it has an unsubscribe
            if not mailing.body_arch or is_html_empty(mailing.body_arch):
                continue
            base_url = self.env['ir.config_parameter'].sudo().get_str('web.base.url')

            root_node = lxml.html.fromstring(mailing.body_arch)
            # this regex will cause a match unless link URL contains /unsubscribe_from_link, causing the URL to be skipped (it will not be returned)
            # @review: I figured using an existing method here would be more practical than rewriting existing logic,
            # but there is an argument to be made that this regex isn't the most intuitively readable. Thoughts?
            skip_regex = r"^((?!/unsubscribe_from_list).)*$"
            link_nodes, urls_and_labels = find_links_with_urls_and_labels(root_node, base_url, skip_regex=skip_regex)
            if len(link_nodes):
                if mailing.warning_message:
                    mailing.warning_message += '\n\n'
                else:
                    mailing.warning_message = ''
                mailing.warning_message += _(
                    'An unsubscribe link is present in this email destined for employees.\n'
                    'Delete it to prevent employees from blacklisting themselves out of company mailings.'
                )
