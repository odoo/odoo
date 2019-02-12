from odoo import api, models, fields


class Wizard(models.TransientModel):
    _name = 'translationn.model'
    _description = "Wizard: translation"

    value = fields.Text(string='Translation Value')
    trans_ids = fields.One2many('ir.translation', 'translation_id')

    @api.multi
    def translation_confirm(self):
        print("---------------------called-------------------------")