from odoo import api, fields, models
from odoo.exceptions import UserError


class GovPagamentoExt(models.Model):
    _inherit = "gov.pagamento"

    tipo = fields.Selection(
        [
            ("normal", "Normal - Remessa Bancaria"),
            ("extra", "Extra - Regularizacao Contabil"),
        ],
        default="normal",
        required=True,
        tracking=True,
        string="Tipo de OP",
        help=(
            "Extra: apenas administradores. Nao gera CNAB. "
            "Uso para regularizacao de pendencias e ajustes."
        ),
    )
    pendencia_id = fields.Many2one(
        "gov.conciliacao.pendencia",
        string="Pendencia Vinculada",
        readonly=True,
        copy=False,
        help="Pendencia de conciliacao que originou esta OP Extra.",
    )

    def _check_tipo_extra_acl(self, tipo):
        if self.env.su:
            return
        if tipo == "extra" and not self.env.user.has_group("gov_base.group_gov_admin"):
            raise UserError(
                "Apenas administradores podem criar ou alterar OP para tipo Extra."
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_tipo_extra_acl(vals.get("tipo", "normal"))
        return super().create(vals_list)

    def write(self, vals):
        if "tipo" in vals:
            self._check_tipo_extra_acl(vals.get("tipo"))
        return super().write(vals)

    def action_enviar_banco(self):
        self.ensure_one()
        if self.tipo == "extra":
            raise UserError(
                'OP Extra nao e enviada ao banco. Use "Confirmar Pagamento" diretamente.'
            )
        return super().action_enviar_banco()

    def action_gerar_cnab_individual(self):
        self.ensure_one()
        if self.tipo == "extra":
            raise UserError("OP Extra nao gera arquivo CNAB.")
        return super().action_gerar_cnab_individual()

    def action_confirmar_pagamento(self):
        self.ensure_one()
        return super().action_confirmar_pagamento()
