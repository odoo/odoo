# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventTrack(models.Model):
    _inherit = 'event.track'
    _mailing_enabled = True
