# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp import api, fields, models
from openerp.http import request

class Website(models.Model):

    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel')


class WebsiteConfigSettings(models.TransientModel):

    _inherit = 'website.config.settings'

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Chat Channel', related='website_id.channel_id')
