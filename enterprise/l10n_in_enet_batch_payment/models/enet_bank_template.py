from odoo import fields, models


class EnetBankTemplate(models.Model):
    _name = 'enet.bank.template'
    _description = 'Enet Bank Template'
    _inherit = ['avatar.mixin']

    name = fields.Char(string="Bank Name", required=True)
    image_1920 = fields.Image(string="Bank Logo")
    bank_configuration = fields.Json(string="Bank Configuration")
