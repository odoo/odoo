# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp import api, fields, models, SUPERUSER_ID
from openerp.http import request

class website(models.Model):

    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Live Chat Channel')


class website_config_settings(models.TransientModel):

    _inherit = 'website.config.settings'

    channel_id = fields.Many2one('im_livechat.channel', string='Live Chat Channel', related='website_id.channel_id')

