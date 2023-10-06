# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class EventShareTag(models.Model):
    _name = 'social.share.tag'
    _description = 'Social Share Campaign Tag'

    name = fields.Char()
