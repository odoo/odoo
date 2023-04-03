# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import format_datetime


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _portal_get_default_format_properties_names(self, options=None):
        """ Add request for rating information """
        properties_names = super()._portal_get_default_format_properties_names()
        if options and options.get('rating_include'):
            properties_names |= {
                'rating',
                'rating_value',
            }
        return properties_names

    def _portal_message_format(self, properties_names):
        vals_list = super()._portal_message_format(properties_names)

        message_to_rating = {}
        if 'rating' in properties_names:
            related_rating = self.env['rating.rating'].sudo().search(
                [('message_id', 'in', self.ids)]
            ).read(
                ["id", "publisher_comment", "publisher_id", "publisher_datetime", "message_id"]
            )
            message_to_rating = {
                rating['message_id'][0]: self._portal_message_format_rating(rating)
                for rating in related_rating
            }

        for message, values in zip(self, vals_list):
            rating_values = message_to_rating.get(message.id, {})
            if rating_values:
                values["rating"] = rating_values

            if 'rating' in properties_names:
                record = self.env[message.model].browse(message.res_id)
                if hasattr(record, 'rating_get_stats'):
                    values['rating_stats'] = record.sudo().rating_get_stats()

        return vals_list

    def _portal_message_format_rating(self, rating_values):
        """ From 'rating_values' (dict coming from reading 'rating.rating') get
        an updated version formatted for frontend display. """
        publisher_name_get = rating_values['publisher_id']
        rating_values['publisher_avatar'] = f'/web/image/res.partner/{publisher_name_get[0]}/avatar_128/50x50' if publisher_name_get else ''
        rating_values['publisher_comment'] = rating_values['publisher_comment'] or ''
        rating_values['publisher_datetime'] = format_datetime(self.env, rating_values['publisher_datetime'])
        rating_values['publisher_id'] = publisher_name_get[0] if publisher_name_get else False
        rating_values['publisher_name'] = publisher_name_get[1] if publisher_name_get else ''
        return rating_values
