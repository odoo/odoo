from odoo import models, fields, api
from odoo.fields import Domain


class PosConfig(models.Model):
    _inherit = 'pos.config'

    module_pos_hardware = fields.Boolean('Use POS Hardware', help="Use available hardware, such as LED strips")
