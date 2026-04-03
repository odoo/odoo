import json

from odoo import fields, models


class GovDocumentBlockCatalog(models.Model):
    """Cataloga os blocos semânticos disponíveis na palette do construtor."""

    _name = "gov.document.block.catalog"
    _description = "Catálogo de Blocos do Documento"
    _order = "sequence asc, name asc, id asc"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    block_kind = fields.Selection(
        [
            ("heading", "Heading"),
            ("legal_basis", "Legal Basis"),
            ("process_field", "Process Field"),
            ("rich_text", "Rich Text"),
            ("table", "Table"),
            ("signature", "Signature"),
            ("bullet_list", "Bullet List"),
            ("conditional", "Conditional"),
            ("metadata", "Metadata"),
            ("divider", "Divider"),
        ],
        required=True,
    )
    category = fields.Char(string="Categoria de agrupamento na palette")
    icon = fields.Char(string="Ícone (emoji ou código)")
    description = fields.Text()
    allowed_document_type_ids = fields.Many2many(
        "gov.document.type",
        string="Tipos Documentais Permitidos",
    )
    default_props_json = fields.Text(string="Props padrão (JSON)")
    typst_renderer_key = fields.Char(string="Chave do renderer Typst")
    supports_children = fields.Boolean(default=False)
    supports_repeat = fields.Boolean(default=False)
    supports_binding = fields.Boolean(default=True)
    is_locked_by_default = fields.Boolean(
        string="Obrigatório por padrão",
        default=False,
    )
    is_system = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    def get_default_props(self):
        self.ensure_one()
        return json.loads(self.default_props_json or "{}")
