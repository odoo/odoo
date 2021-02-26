# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class RpcSystem(models.AbstractModel):
    _name = 'system'
    _description = "RPC system"

    def noop(self):
        pass
