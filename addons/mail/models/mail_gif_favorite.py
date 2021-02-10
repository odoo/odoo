# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class GifFavorite(models.Model):
    _name = 'mail.gif_favorite'
    _description = 'Save favorite gif from tenor.io API'

    gif_id = fields.Integer('Gif id from tenor.io', required=True, index=True)
