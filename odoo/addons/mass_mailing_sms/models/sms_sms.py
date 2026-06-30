# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import fields, models, tools


class SmsSms(models.Model):
    _inherit = ['sms.sms']

    mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')
    # Linking to another field than the comodel id allows to use the ORM to create
    # "linked" records (see _prepare_sms_values) without adding a foreign key.
    # See commit message for why this is useful.
    mailing_trace_ids = fields.One2many('mailing.trace', 'sms_id_int', string='Statistics')

    def _update_body_short_links(self):
        """ Override to tweak shortened URLs by adding statistics ids, allowing to
        find customer back once clicked. """
        res = dict.fromkeys(self.ids, False)
        for sms in self:
            if not sms.mailing_id or not sms.body:
                res[sms.id] = sms.body
                continue

            body = sms.body
            for url in set(re.findall(tools.TEXT_URL_REGEX, body)):
                if url.startswith(sms.get_base_url() + '/r/'):
                    body = re.sub(re.escape(url) + r'(?![\w@:%.+&~#=/-])', url + f'/s/{sms.id}', body)
            res[sms.id] = body
        return res
