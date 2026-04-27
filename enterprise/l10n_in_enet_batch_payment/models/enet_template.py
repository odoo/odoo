from odoo import fields, models


class EnetTemplate(models.Model):
    _name = 'enet.template'
    _description = 'ENet Template'

    sequence = fields.Integer()
    field_name = fields.Char(string="Field Name")
    label = fields.Char(string="Label", required=True)
    journal_id = fields.Many2one('account.journal', ondelete='cascade', default=lambda self: self.env.context.get('active_id'))
