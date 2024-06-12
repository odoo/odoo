from odoo import models, fields, api


class ResUsers(models.Model):
    
    _inherit = 'res.users'
    
    #----------------------------------------------------------
    # Properties
    #----------------------------------------------------------
    
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'chatter_position',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'chatter_position',
        ]

    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    chatter_position = fields.Selection(
        selection=[
            ('side', 'Side'),
            ('bottom', 'Bottom'),
        ], 
        string="Chatter Position",
        default='side',
        required=True,
    )
