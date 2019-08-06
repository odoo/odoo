# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.tools import plaintext2html, html2plaintext


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _portal_message_format(self, field_list):
        # inlude rating value in data if requested
        if self._context.get('rating_include'):
            field_list += ['rating_value']
        return super(MailMessage, self)._portal_message_format(field_list)

    def _message_read_dict_postprocess(self, message_values, message_tree):
        """
        Overide the method to add information about a publisher comment
        on each rating messages (if rating value is requested).
        """
        res = super(MailMessage, self)._message_read_dict_postprocess(message_values, message_tree)

        if self._context.get('rating_include'):
            rating = request.env['rating.rating']
            infos = ["id", "publisher_comment", "publisher_id", "publisher_date", "message_id"]
            related_rating = rating.search([('message_id', 'in', self.ids)]).read(infos)
            rr_tree = dict((int(rr['message_id'][0]), rr) for rr in related_rating)
            for m_v in message_values:
                # Publisher comment info
                if m_v['id'] in rr_tree:
                    m_v["rating"] = rr_tree[m_v['id']]
                    if m_v["rating"]["publisher_comment"]:
                        m_v["rating"]["publisher_comment_plaintext"] = html2plaintext(m_v["rating"]["publisher_comment"])
                else:
                    m_v["rating"] = {}
        return res
