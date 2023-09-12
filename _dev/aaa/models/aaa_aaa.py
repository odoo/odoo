from odoo import models, fields


class AaaModel(models.Model):
    _name = "crm.aaa.aaa"
    _description = "aaa CRM Recurring revenue plans"
    _order = "sequence"

    name = fields.Char(string="Account Name", required=True)
    code = fields.Char(size=64, required=True)
    remark = fields.Char(string="Remark", required=False)
    sequence = fields.Integer(string="sequence", required=False, default=100)
