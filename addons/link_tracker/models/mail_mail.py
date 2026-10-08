from __future__ import annotations

import re

from odoo import models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _prepare_outgoing_body(self):
        self.ensure_one()
        body = super()._prepare_outgoing_body()
        disable_link_tracking = self.env['ir.config_parameter'].get_param('link_tracker.disable_link_tracking', 'False').upper()
        record = self.env[self.model].browse(self.res_id) if (self.model and self.res_id) else self
        if disable_link_tracking not in ["TRUE", "YES", "1"] and record._mail_get_partners()[record.id].country_code not in disable_link_tracking:
            return body
        codes = [codes[0] for codes in re.findall(r'\/r\/(\w+)(/\w/\w+)?', body)]
        if not codes:
            return body
        tracked_urls = self.env['link.tracker'].search([('link_code_ids.code', 'in', codes)]).mapped(lambda tracker: (tracker.short_url, tracker.url))
        for tracked_short_url, tracked_url in tracked_urls:
            body = body.replace(tracked_short_url, tracked_url)
        return body
