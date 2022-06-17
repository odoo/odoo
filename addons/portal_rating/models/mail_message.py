# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _portal_message_format(self, field_list):
        # inlude rating value in data if requested
        if self._context.get('rating_include'):
            field_list += ['rating_value']
        return super(MailMessage, self)._portal_message_format(field_list)

    def _message_format(self, fnames, format_reply=True, legacy=False):
        """ Override the method to add information about a publisher comment
        on each rating messages if requested, and compute a plaintext value of it.
        """
        vals_list = super(MailMessage, self)._message_format(fnames, format_reply=format_reply, legacy=legacy)

        if self._context.get('rating_include'):
            infos = ["id", "publisher_comment", "publisher_id", "publisher_datetime", "message_id"]
            related_rating = self.env['rating.rating'].sudo().search([('message_id', 'in', self.ids)]).read(infos)
            mid_rating_tree = dict((rating['message_id'][0], rating) for rating in related_rating)
            for vals in vals_list:
                vals["rating"] = mid_rating_tree.get(vals['id'], {})
        return vals_list
