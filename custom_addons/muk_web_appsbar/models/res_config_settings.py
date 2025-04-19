from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    appbar_image = fields.Binary(
        related='company_id.appbar_image',
        readonly=False
    )
