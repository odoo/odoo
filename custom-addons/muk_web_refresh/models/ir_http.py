from odoo import models


class IrHttp(models.AbstractModel):

    _inherit = 'ir.http'

    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------
    
    def session_info(self):
        result = super().session_info()
        result['pager_autoload_interval'] = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'muk_web_refresh.pager_autoload_interval', 
                default=30000
            )
        )
        return result
