from odoo import fields, models


class GovAuditoriaChecklistTemplate(models.Model):
    _name = "gov.auditoria.checklist.template"
    _description = "Checklist Template for Control Body"
    _order = "orgao_id, sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    orgao_id = fields.Many2one(
        "gov.auditoria.orgao",
        required=True,
        ondelete="cascade",
        index=True,
    )
    item_ids = fields.One2many(
        "gov.auditoria.checklist.template.item",
        "template_id",
        string="Items",
    )


class GovAuditoriaChecklistTemplateItem(models.Model):
    _name = "gov.auditoria.checklist.template.item"
    _description = "Checklist Template Item"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "gov.auditoria.checklist.template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    descricao = fields.Char(required=True)
    obrigatorio = fields.Boolean(default=True)
