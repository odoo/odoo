from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        res['web.base.url'] = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='')
        return res
