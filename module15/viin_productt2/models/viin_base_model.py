
from odoo import   models, fields


class ViinBaseModel(models.AbstractModel):
        _name = 'viin.base.model'
        _description = 'Viin base model'
        active = fields.Boolean(string='IsActive', default = True)

    

