from odoo import models, api
from odoo.modules.loading import force_demo


class IrDemo(models.TransientModel):

    _name = 'ir.demo'

    @api.model
    def install_demo(self):
        force_demo(self.env.cr)
