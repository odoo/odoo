from odoo import fields, models


class TestIrQwebFields(models.Model):
    _name = 'test_ir_qweb_fields'
    _description = 'Test ir.qweb.fields Model'

    char = fields.Char()
    integer = fields.Integer()
    float = fields.Float()
    numeric = fields.Float(digits=(16, 2))
    monetary = fields.Float(digits=(16, 55))
    many2one = fields.Many2one('test_ir_qweb_fields.relations')
    binary = fields.Binary(attachment=False)
    date = fields.Date()
    datetime = fields.Datetime()
    selection = fields.Selection([
        ('A', "Qu'il n'est pas arrivé à Toronto"),
        ('B', "Qu'il était supposé arriver à Toronto"),
        ('C', "Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?"),
        ('D', "La réponse D"),
    ], string="Lorsqu'un pancake prend l'avion à destination de Toronto et "
              "qu'il fait une escale technique à St Claude, on dit:")
    html = fields.Html()
    text = fields.Text()


class TestIrQwebFieldsRelations(models.Model):
    # This model is used to set up 'test_ir_qweb_fields' relations.
    _name = 'test_ir_qweb_fields.relations'
    _description = 'Test ir.qweb.fields Relations'

    name = fields.Char()
