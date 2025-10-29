from odoo import fields, models


class Test_Indexed_Translation(models.Model):
    _name = 'test_indexed_translation.model'
    _description = 'A model to indexed translated fields'

    name = fields.Text('Name trigram', translate=True, index='trigram')
