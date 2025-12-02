from odoo import models


class IrHttp(models.AbstractModel):

    _inherit = "ir.http"

    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------
    
    def session_info(self):
        result = super().session_info()
        result['chatter_position'] = self.env.user.chatter_position
        return result
