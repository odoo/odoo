from odoo import fields, models


class GovAuditoriaOrgao(models.Model):
    _name = "gov.auditoria.orgao"
    _description = "Control Body"
    _order = "tipo, sigla, name"

    name = fields.Char(required=True)
    sigla = fields.Char(required=True)
    tipo = fields.Selection(
        [
            ("tce", "TCE"),
            ("tcm", "TCM"),
            ("tcu", "TCU"),
            ("cge", "CGE"),
            ("cgm", "CGM"),
            ("outro", "Outro"),
        ],
        required=True,
        default="tce",
    )
    estado_id = fields.Many2one("res.country.state", string="UF")
    prazo_remessa_dias = fields.Integer(default=30)
    prazo_defesa_dias = fields.Integer(default=15)
    prazo_recurso_dias = fields.Integer(default=15)
    checklist_template_ids = fields.One2many(
        "gov.auditoria.checklist.template",
        "orgao_id",
        string="Checklist Templates",
    )
    estados_obrigatorios = fields.Char(
        help="Comma-separated cycle states that should not be skipped for this body."
    )
    instrucao_normativa = fields.Char()
    portal_url = fields.Char()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("gov_auditoria_orgao_sigla_unique", "unique(sigla)", "A sigla do orgao deve ser unica."),
    ]
