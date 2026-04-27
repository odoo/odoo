from odoo import models
from odoo.tools.mail import TEXT_URL_REGEX

import re
import logging
from urllib3.exceptions import LocationParseError


_logger = logging.getLogger(__name__)


class WhatsAppTemplate(models.Model):
    _inherit = 'whatsapp.template'

    def _get_additional_button_values(self, button):
        """
        Checks if the provided `website_url` is already being tracked. This is important due to
        the added functionality that allows users to send tracked links as website buttons (see _get_url_button_data).
        Additionally, local variables that aren't sent from Meta need to be synchronized to prevent
        their values from being lost.
        """
        button_url_data = super()._get_additional_button_values(button)
        if 'sequence' not in button or button['button_type'] != 'url':
            return {}
        btn_before_sync = self.button_ids.filtered(lambda x: x.sequence == button.get('sequence'))
        if not btn_before_sync:
            return button_url_data

        if btn_before_sync.url_type == 'tracked':
            button_url_data['url_type'] = 'tracked'
            button_url_data['website_url'] = btn_before_sync.website_url
        return button_url_data

    def _get_send_template_vals(self, record, whatsapp_message):
        """Override to create link tracker before whatsapp messages are sent"""

        template_vals, attachment = super()._get_send_template_vals(
            record, whatsapp_message
        )
        campaign_id = whatsapp_message.sudo().marketing_trace_ids.activity_id.campaign_id

        mail_mixin = self.env['mail.render.mixin']
        if not template_vals.get('components') or not campaign_id:
            return template_vals, attachment

        tracker_values = {
            'campaign_id': campaign_id.utm_campaign_id.id,
        }

        # check button links
        for component in template_vals['components']:
            if component['type'] == 'button' and component['sub_type'] == 'url':
                button = self.button_ids.filtered(lambda btn: btn.sequence == component['index'])
                if button.url_type == 'tracked':
                    website_url = button.website_url
                    shortened_link = mail_mixin.sudo()._shorten_links_text(
                                        website_url, tracker_values
                                    )
                    shortened_link = shortened_link + f'/w/{whatsapp_message.id}'
                    component['parameters'][0]['text'] = shortened_link.replace(self.env['link.tracker'].get_base_url(), '').lstrip('/')

        # check variable links
        url_template_parameters = [
            parameter
            for component in template_vals['components']
            if component['type'] == 'body'
            for parameter in component['parameters']
            if parameter['type'] == 'text'
            and re.match(TEXT_URL_REGEX, parameter['text']) is not None
        ]

        for tmpl_param in url_template_parameters:
            try:
                shortened_link = mail_mixin.sudo()._shorten_links_text(
                    tmpl_param['text'], tracker_values
                )
                shortened_link = shortened_link + f'/w/{whatsapp_message.id}'
            except LocationParseError as e:
                _logger.warning(
                    "Could not shorten link: %s, the error was risen: %s",
                    tmpl_param['text'],
                    str(e)
                )
                shortened_link = tmpl_param['text']
            tmpl_param['text'] = shortened_link
        return template_vals, attachment

    def _get_url_button_data(self, button):
        """Return button component for template registration to whatsapp"""
        button_data = super()._get_url_button_data(button)
        if button.url_type == 'tracked':
            base_url = self.env['link.tracker'].get_base_url().strip('/')
            button_data.update({
                'url': base_url + '/{{1}}',
                'example': base_url + '/???'
            })
        return button_data
