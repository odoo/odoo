# -*- coding: utf-8 -*-_
from openerp import models, fields, api, _

class signature_item(models.Model):
    _name = "signature.item"
    _description = "Signature Field For Document To Sign"

    template_id = fields.Many2one('signature.request.template', string="Document Template", required=True, ondelete='cascade')

    type_id = fields.Many2one('signature.item.type', string="Type", required=True, ondelete='cascade')

    required = fields.Boolean(default=True)
    responsible_id = fields.Many2one("signature.item.party", string="Responsible")

    page = fields.Integer(string="Document Page", required=True, default=1)
    posX = fields.Float(digits=(4, 3), string="Position X", required=True)
    posY = fields.Float(digits=(4, 3), string="Position Y", required=True)
    width = fields.Float(digits=(4, 3), required=True)
    height = fields.Float(digits=(4, 3), required=True)

    @api.multi
    def getByPage(self):
        items = {}
        for item in self:
            if item.page not in items:
                items[item.page] = []
            items[item.page].append(item)
        return items

class signature_item_type(models.Model):
    _name = "signature.item.type"
    _description = "Specialized type for signature fields"

    name = fields.Char(string="Field Name", required=True)
    type = fields.Selection([
        ('signature', "Signature"),
        ('initial', "Initial"),
        ('text', "Text"),
        ('textarea', "Multiline Text"),
    ], required=True, default='text')

    tip = fields.Char(required=True, default="fill in")
    placeholder = fields.Char()

    default_width = fields.Float(string="Default Width", digits=(4, 3), required=True, default=0.150)
    default_height = fields.Float(string="Default Height", digits=(4, 3), required=True, default=0.015)
    auto_field = fields.Char(string="Automatic Partner Field", help="Partner field to use to auto-complete the fields of this type")

class signature_item_value(models.Model):
    _name = "signature.item.value"
    _description = "Signature Field Value For Document To Sign"
    
    signature_item_id = fields.Many2one('signature.item', string="Signature Item", required=True, ondelete='cascade')
    signature_request_id = fields.Many2one('signature.request', string="Signature Request", required=True, ondelete='cascade')

    value = fields.Text()

class signature_item_party(models.Model):
    _name = "signature.item.party"
    _description = "Type of partner which can access a particular signature field"

    name = fields.Char(required=True)
