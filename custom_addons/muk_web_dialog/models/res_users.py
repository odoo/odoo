from odoo import models, fields, api


class ResUsers(models.Model):
    
    _inherit = 'res.users'
    
    #----------------------------------------------------------
    # Properties
    #----------------------------------------------------------
    
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'dialog_size',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'dialog_size',
        ]

    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    dialog_size = fields.Selection(
        selection=[
            ('minimize', 'Minimize'),
            ('maximize', 'Maximize'),
        ], 
        string="Dialog Size",
        default='minimize',
        required=True,
    )
