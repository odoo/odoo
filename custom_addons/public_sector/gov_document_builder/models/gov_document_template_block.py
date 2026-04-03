import uuid

from odoo import api, fields, models


class GovDocumentTemplateBlock(models.Model):
    """Representa um nó de bloco dentro da árvore visual de um template."""

    _name = "gov.document.template.block"
    _description = "Bloco do Template de Documento"
    _order = "sequence asc, id asc"

    template_id = fields.Many2one(
        "gov.document.template",
        required=True,
        ondelete="cascade",
        string="Template",
    )
    catalog_block_id = fields.Many2one(
        "gov.document.block.catalog",
        required=True,
        string="Bloco de Catálogo",
    )
    sequence = fields.Integer(default=10)
    parent_block_id = fields.Many2one(
        "gov.document.template.block",
        ondelete="set null",
        string="Bloco Pai",
    )
    node_uuid = fields.Char(string="UUID do Nó", readonly=True)
    props_json = fields.Text(string="Propriedades (JSON)")
    binding_json = fields.Text(string="Binding (JSON)")
    visibility_rule = fields.Char(string="Regra de Visibilidade")
    required = fields.Boolean(string="Obrigatório", default=False)
    locked = fields.Boolean(string="Travado", default=False)
    allow_delete = fields.Boolean(default=True)
    allow_move = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            prepared_vals = dict(vals)
            prepared_vals.setdefault("node_uuid", str(uuid.uuid4()))
            prepared_vals_list.append(prepared_vals)
        return super().create(prepared_vals_list)
