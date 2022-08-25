# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventTrack(models.Model):
    _inherit = 'event.track'
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        return [('stage_id.is_cancel', '=', False)]
