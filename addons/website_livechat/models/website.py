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



class ir_ui_view(osv.Model):

    _inherit = "ir.ui.view"

    def _prepare_qcontext(self, cr, uid, context=None):
        qcontext = super(ir_ui_view, self)._prepare_qcontext(cr, uid, context=context)
        if request and getattr(request, 'website_enabled', False):
            if request.website.channel_id:
                qcontext['website_livechat_url'] = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')
                qcontext['website_livechat_dbname'] = cr.dbname
                qcontext['website_livechat_channel'] = request.website.channel_id.id
        return qcontext
