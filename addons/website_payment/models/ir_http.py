# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        website_sudo = self.env['website'].sudo().get_current_website()
        if website_sudo:
            session_info['website_currency_id'] = website_sudo.get_website_currency().id
        return session_info
