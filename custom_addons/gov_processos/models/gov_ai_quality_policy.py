from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .constants import DOC_TYPE_SELECTION, PROCESS_TYPE_SELECTION


class GovAiQualityPolicy(models.Model):
    _name = "gov.ai.quality.policy"
    _description = "Política de Qualidade para Geração IA"
    _order = "doc_type, sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    doc_type = fields.Selection(
        DOC_TYPE_SELECTION,
        string="Tipo de Documento",
        required=True,
    )
    process_type = fields.Selection(
        PROCESS_TYPE_SELECTION,
        string="Tipo de Processo (filtro)",
        help=(
            "Vazio = aplica a todos os tipos. "
            "Ex.: compras_servicos, contratacao_direta."
        ),
    )

    num_passagens = fields.Integer(
        string="Número de Passagens",
        default=2,
        help=(
            "1 = geração direta; 2 = rascunho + revisão; "
            "3 = rascunho + revisão jurídica + ajuste."
        ),
    )
    passagem_1_instrucao = fields.Text(
        string="Instrução Passagem 1 (Rascunho)",
    )
    passagem_2_instrucao = fields.Text(
        string="Instrução Passagem 2 (Revisão Jurídica)",
    )
    passagem_3_instrucao = fields.Text(
        string="Instrução Passagem 3 (Ajuste Final)",
    )

    validar_artigos_lei = fields.Boolean(
        string="Validar referências à Lei 14.133",
        default=True,
    )
    validar_campos_obrigatorios = fields.Boolean(
        string="Validar campos obrigatórios AGU",
        default=True,
    )
    validar_valores_monetarios = fields.Boolean(
        string="Validar valores monetários",
        default=True,
    )
    min_palavras = fields.Integer(
        string="Mínimo de palavras",
        default=200,
    )

    estado_apos_geracao = fields.Selection(
        [
            ("rascunho", "Manter como Rascunho"),
            ("revisao", "Enviar para Revisão Humana"),
        ],
        string="Estado após Geração",
        default="revisao",
    )
    notificar_responsavel = fields.Boolean(
        string="Notificar Responsável pelo Processo",
        default=True,
    )
    exigir_aprovacao_humana = fields.Boolean(
        string="Exigir Aprovação Humana antes de Assinar",
        default=True,
        help=(
            "Se marcado, documentos gerados por IA não podem ser assinados "
            "sem passar por aprovação manual."
        ),
    )
    prompt_validacao = fields.Text(
        string="Prompt de Auto-validação (Passagem Extra)",
        help=(
            "Opcional. Se preenchido, roda uma passagem adicional para gerar "
            "avaliação estruturada (score e observações)."
        ),
    )

    @api.constrains("num_passagens")
    def _check_num_passagens(self):
        for rec in self:
            if rec.num_passagens < 1 or rec.num_passagens > 3:
                raise ValidationError("Número de passagens deve estar entre 1 e 3.")

    @api.constrains("min_palavras")
    def _check_min_palavras(self):
        for rec in self:
            if rec.min_palavras < 0:
                raise ValidationError("Mínimo de palavras não pode ser negativo.")
