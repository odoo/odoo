from odoo import api, fields, models


class GovDocumentFieldDefinition(models.Model):
    _name = "gov.document.field.definition"
    _description = "Definição de Campo de Documento"
    _order = "namespace asc, sequence asc, id asc"

    name = fields.Char(string="Nome", required=True)
    namespace = fields.Selection(
        [
            ("process", "Processo"),
            ("legal", "Base Legal"),
            ("procurement", "Contratação"),
            ("auction", "Licitação"),
            ("contract", "Contrato"),
            ("budget", "Orçamento"),
            ("execution", "Execução"),
            ("reconciliation", "Conciliação"),
        ],
        string="Namespace",
        required=True,
    )
    variable_key = fields.Char(string="Chave da Variável", required=True)
    value_type = fields.Selection(
        [
            ("text", "Texto"),
            ("date", "Data"),
            ("currency", "Moeda"),
            ("percent", "Percentual"),
            ("integer", "Inteiro"),
            ("boolean", "Booleano"),
            ("list", "Lista"),
        ],
        string="Tipo de Valor",
        required=True,
        default="text",
    )
    mutability_policy = fields.Selection(
        [
            ("immutable", "Imutável"),
            ("snapshot", "Snapshot"),
            ("dynamic", "Dinâmico"),
        ],
        string="Política de Mutabilidade",
        required=True,
        default="immutable",
    )
    default_transformer = fields.Char(string="Transformer Padrão")
    example_value = fields.Char(string="Valor de Exemplo")
    description = fields.Text(string="Descrição")
    sequence = fields.Integer(string="Sequência", default=10)
    active = fields.Boolean(string="Ativo", default=True)
    display_path = fields.Char(
        string="Caminho",
        compute="_compute_display_path",
    )

    _namespace_variable_key_unique = models.Constraint(
        "unique(namespace, variable_key)",
        "Já existe uma definição para esta variável neste namespace.",
    )

    @api.depends("namespace", "variable_key")
    def _compute_display_path(self):
        for rec in self:
            if rec.namespace and rec.variable_key:
                rec.display_path = f"{rec.namespace}.{rec.variable_key}"
            else:
                rec.display_path = ""
