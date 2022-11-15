from odoo import fields, models

class BaseDucation(models.AbstractModel):
    _name = 'base.education'

    active = fields.Boolean(string='Active')
    def do_active(self):
        for r in self:
            r.active = not r.active
            
            
            