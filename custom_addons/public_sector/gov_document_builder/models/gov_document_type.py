from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovDocumentType(models.Model):
    """Define os tipos documentais base usados pelo construtor de documentos."""

    _name = "gov.document.type"
    _description = "Tipo Documental"

    name = fields.Char(string="Tipo Documental", required=True)
    code = fields.Char(
        string="Código",
        required=True,
        help="Ex.: dfd, tr, dispensa_just.",
    )
    description = fields.Text(string="Descrição")
    active = fields.Boolean(default=True)
    process_model = fields.Char(
        string="Modelo do Processo",
        help="Ex: gov.procurement.process",
    )
    typst_package_ref = fields.Char(string="Pacote Typst Base")
    versioning_policy = fields.Selection(
        [
            ("manual", "Manual"),
            ("auto", "Automático"),
        ],
        string="Política de Versionamento",
        default="manual",
    )
    template_ids = fields.One2many(
        "gov.document.template",
        "document_type_id",
        string="Templates",
    )

    _sql_constraints = [
        (
            "gov_document_type_code_active_uniq",
            "unique(code, active)",
            "Já existe um tipo documental com este código para este estado de ativação.",
        ),
    ]

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            code = rec.code or ""
            if code != code.lower() or any(char.isspace() for char in code):
                raise ValidationError(
                    "O código do tipo documental deve estar em lowercase e sem espaços."
                )
