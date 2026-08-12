from odoo import fields, models


class TestOrmIndexedTranslation(models.Model):
    _name = 'test_orm.indexed_translation'
    _description = 'A model to indexed translated fields'

    name = fields.Text('Name trigram', translate=True, index='trigram')
