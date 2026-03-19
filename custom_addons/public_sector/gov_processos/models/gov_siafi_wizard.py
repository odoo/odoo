import base64
import hashlib
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GovSiafiWizard(models.TransientModel):
    _name = "gov.siafi.wizard"
    _description = "Exportacao SIAFI - Execucao Orcamentaria"

    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    exercicio = fields.Integer(
        string="Exercicio",
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    data_ini = fields.Date(
        string="Data Inicio",
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1),
    )
    data_fim = fields.Date(
        string="Data Fim",
        required=True,
        default=fields.Date.today,
    )
    incluir_ne = fields.Boolean(string="Incluir NEs", default=True)
    incluir_nl = fields.Boolean(string="Incluir NLs", default=True)
    incluir_op = fields.Boolean(string="Incluir OPs", default=True)
    state_ne = fields.Selection(
        [
            ("todos", "Todos"),
            ("emitido", "Apenas emitidas"),
        ],
        default="emitido",
        string="Estado NE",
    )
    state_op = fields.Selection(
        [
            ("todos", "Todos"),
            ("pago", "Apenas pagas"),
        ],
        default="pago",
        string="Estado OP",
    )

    preview_resumo = fields.Text(
        string="Resumo do periodo",
        compute="_compute_preview",
        store=False,
    )

    arquivo_txt = fields.Binary(string="Arquivo TXT", readonly=True)
    arquivo_nome = fields.Char(readonly=True)
    hash_sha256 = fields.Char(readonly=True)
    gerado = fields.Boolean(default=False)

    @api.depends(
        "ug_id",
        "exercicio",
        "data_ini",
        "data_fim",
        "incluir_ne",
        "incluir_nl",
        "incluir_op",
        "state_ne",
        "state_op",
    )
    def _compute_preview(self):
        for rec in self:
            try:
                nes, nls, ops = rec._buscar_registros()
                total_ne = rec._sum_field(nes, "valor_empenho")
                total_nl = rec._sum_field(nls, "valor_liquidado")
                total_op = rec._sum_field(ops, "valor")
                rec.preview_resumo = (
                    f"NEs encontradas:  {len(nes)}\n"
                    f"NLs encontradas:  {len(nls)}\n"
                    f"OPs encontradas:  {len(ops)}\n"
                    f"Total NE: R$ {total_ne:,.2f}\n"
                    f"Total NL: R$ {total_nl:,.2f}\n"
                    f"Total OP: R$ {total_op:,.2f}"
                )
            except Exception as exc:
                _logger.warning("Preview SIAFI falhou: %s", exc)
                rec.preview_resumo = f"Erro ao calcular preview: {exc}"

    def _sum_field(self, records, field_name):
        total = 0.0
        for rec in records:
            total += float(getattr(rec, field_name, 0.0) or 0.0)
        return total

    def _buscar_registros(self):
        self.ensure_one()

        has_ne = "gov.empenho" in self.env
        has_nl = "gov.liquidacao" in self.env
        has_op = "gov.pagamento" in self.env

        NE = self.env["gov.empenho"] if has_ne else False
        NL = self.env["gov.liquidacao"] if has_nl else False
        OP = self.env["gov.pagamento"] if has_op else False

        nes = []
        nls = []
        ops = []

        if has_ne and self.incluir_ne:
            domain_ne = [
                ("ug_id", "=", self.ug_id.id),
                ("exercicio", "=", self.exercicio),
            ]
            if self.state_ne == "emitido":
                domain_ne.append(("state", "=", "emitido"))
            nes = NE.search(domain_ne)

        if has_nl and self.incluir_nl:
            domain_nl = [
                ("ug_id", "=", self.ug_id.id),
                ("exercicio", "=", self.exercicio),
                ("data_liquidacao", ">=", self.data_ini),
                ("data_liquidacao", "<=", self.data_fim),
            ]
            nls = NL.search(domain_nl)

        if has_op and self.incluir_op:
            domain_op = [
                ("ug_id", "=", self.ug_id.id),
                ("exercicio", "=", self.exercicio),
                ("data_pagamento", ">=", self.data_ini),
                ("data_pagamento", "<=", self.data_fim),
            ]
            if self.state_op == "pago":
                domain_op.append(("state", "=", "pago"))
            ops = OP.search(domain_op)

        return nes, nls, ops

    def action_exportar(self):
        self.ensure_one()
        from .gov_siafi_service import GovSiafiService

        nes, nls, ops = self._buscar_registros()
        if not (nes or nls or ops):
            raise UserError(
                "Nenhum registro encontrado para os filtros informados. "
                "Verifique periodo e estados."
            )

        dados = {
            "ug_codigo": str(self.ug_id.id).zfill(6),
            "ug_nome": self.ug_id.name,
            "exercicio": self.exercicio,
            "data_geracao": fields.Date.today(),
            "operador": self.env.user.name,
            "nes": nes,
            "nls": nls,
            "ops": ops,
        }

        txt_bytes = GovSiafiService.exportar(dados)
        sha256 = hashlib.sha256(txt_bytes).hexdigest()
        fname = (
            f"SIAFI_{self.ug_id.name}_{self.exercicio}_{fields.Date.today()}.txt"
        ).replace(" ", "_")

        self.write(
            {
                "arquivo_txt": base64.b64encode(txt_bytes).decode("ascii"),
                "arquivo_nome": fname,
                "hash_sha256": sha256,
                "gerado": True,
            }
        )
        return self._reabrir()

    def _reabrir(self):
        self.invalidate_recordset()
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.siafi.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_abrir_wizard(self):
        wizard = self.env["gov.siafi.wizard"].create(
            {
                "ug_id": self.env.company.id,
                "exercicio": fields.Date.today().year,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Exportar SIAFI",
            "res_model": "gov.siafi.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
