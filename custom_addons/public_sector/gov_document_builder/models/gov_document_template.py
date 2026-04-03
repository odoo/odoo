import json
import re

from odoo import fields, models


class GovDocumentTemplate(models.Model):
    """Armazena templates visuais reutilizáveis para cada tipo documental."""

    _name = "gov.document.template"
    _description = "Template de Documento"
    _order = "name asc, version desc, id desc"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    document_type_id = fields.Many2one(
        "gov.document.type",
        required=True,
        ondelete="restrict",
        string="Tipo Documental",
    )
    version = fields.Char(default="1.0")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        string="Empresa",
    )
    layout_schema_json = fields.Text(string="AST Visual Inicial (JSON)")
    default_context_json = fields.Text(string="Contexto Padrão (JSON)")
    typst_preamble = fields.Text(string="Preâmbulo Typst")
    typst_style_profile = fields.Char(string="Perfil de Estilo Typst")
    notes = fields.Text(string="Notas")
    block_template_ids = fields.One2many(
        "gov.document.template.block",
        "template_id",
        string="Blocos do Template",
    )
    instance_count = fields.Integer(
        compute="_compute_instance_count",
        string="Total de Instâncias",
    )

    def _compute_instance_count(self):
        DocumentInstance = self.env.get("gov.document.instance")
        for rec in self:
            if DocumentInstance is not None:
                rec.instance_count = DocumentInstance.search_count([("template_id", "=", rec.id)])
            else:
                rec.instance_count = 0

    def get_layout_schema(self):
        self.ensure_one()
        return json.loads(self.layout_schema_json or "[]")

    def copy(self, default=None):
        copies = self.browse()
        for rec in self:
            rec_default = dict(default or {})
            rec_default.setdefault("version", rec._get_next_version())
            copies |= super(GovDocumentTemplate, rec).copy(default=rec_default)
        return copies

    def _get_next_version(self):
        self.ensure_one()
        version = (self.version or "1.0").strip()
        match = re.match(r"^(.*?)(\d+)$", version)
        if not match:
            return f"{version}.1" if version else "1.1"
        prefix, number = match.groups()
        return f"{prefix}{int(number) + 1}"
