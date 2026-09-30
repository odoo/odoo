from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def lazy_session_info(self):
        res = super().lazy_session_info()
        res['show_sale_receipts'] = self.env['ir.config_parameter'].sudo().get_param('account.show_sale_receipts')
        return res
