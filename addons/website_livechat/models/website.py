# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp import api, fields, models
from openerp.http import request

class Website(models.Model):

    _inherit = "website"

    channel_id = fields.Many2one('im_livechat.channel', string='Live Chat Channel')


class WebsiteConfigSettings(models.TransientModel):

    _inherit = 'website.config.settings'

    channel_id = fields.Many2one('im_livechat.channel', string='Live Chat Channel', related='website_id.channel_id')



class IrUiView(models.Model):

    _inherit = "ir.ui.view"

    @api.model
    def _prepare_qcontext(self):
        qcontext = super(IrUiView, self)._prepare_qcontext()
        if request and getattr(request, 'website_enabled', False):
            if request.website.channel_id:
                qcontext['website_livechat_url'] = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                qcontext['website_livechat_dbname'] = self._cr.dbname
                qcontext['website_livechat_channel'] = request.website.channel_id.id
        return qcontext
