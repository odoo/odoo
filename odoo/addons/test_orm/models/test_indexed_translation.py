from odoo import api, fields, models


class TestIndexedTranslationIndexedTranslation(models.Model):
    _name = 'test_indexed_translation.indexed_translation'
    _description = 'A model to indexed translated fields'

    name = fields.Text('Name trigram', translate=True, index='trigram')