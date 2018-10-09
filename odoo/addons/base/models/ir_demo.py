from odoo import models
from odoo.modules.loading import force_demo


class IrDemo(models.TransientModel):

    _name = 'ir.demo'
    _description = 'Demo'

    def install_demo(self):
        force_demo(self.env.cr)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/web',
        }
