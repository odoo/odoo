# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SocialShareFieldAllow(models.Model):
    _name = 'social.share.field.allow'
    _description = 'Field allowed in social share templates'

    field_id = fields.Many2one('ir.model.fields')
