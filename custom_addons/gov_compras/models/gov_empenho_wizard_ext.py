from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class GovEmpenhoWizard(models.TransientModel):
    _inherit = "gov.empenho.wizard"

    compras_item_track_id = fields.Many2one(
        "gov.compras.item.track",
        string="Item de Compra (Rastreio)",
        domain="[('processo_id', '=', processo_id), ('status', 'in', ('nad','licitado','empenhado','encerrado'))]",
        help="ID de rastreio do item vinculado a esta NE.",
    )

    @api.onchange("compras_item_track_id")
    def _onchange_compras_item_track_id(self):
        for rec in self:
            track = rec.compras_item_track_id
            if not track:
                continue
            if not rec.valor_empenho:
                rec.valor_empenho = (
                    track.valor_arrematado
                    or track.valor_estimado_ref
                    or track.preco_referencia_conservador
                    or rec.valor_empenho
                )
            if not rec.objeto and track.descricao:
                rec.objeto = track.descricao

    @api.constrains("processo_id", "compras_item_track_id")
    def _check_track_obrigatorio(self):
        for rec in self:
            if not rec.processo_id:
                continue
            if not rec.compras_item_track_id:
                raise ValidationError(
                    "Selecione o ID de rastreio para emitir NE vinculada ao processo."
                )
            if rec.compras_item_track_id.processo_id != rec.processo_id:
                raise ValidationError(
                    "O ID de rastreio informado pertence a outro processo."
                )

    def action_emitir_ne(self):
        self.ensure_one()

        if not self.credor_id:
            raise UserError("Informe o credor do empenho.")
        if (self.valor_empenho or 0.0) <= 0:
            raise UserError("Valor do empenho deve ser maior que zero.")

        ne = self.env["gov.empenho"].create(
            {
                "ug_id": self.processo_id.ug_id.id,
                "exercicio": self.exercicio,
                "credor_id": self.credor_id.id,
                "tipo_empenho": self.tipo_empenho,
                "valor_empenho": self.valor_empenho,
                "data_empenho": self.data_empenho,
                "data_vencimento": self.data_vencimento or False,
                "objeto": self.objeto,
                "programa": self.programa or "",
                "acao": self.acao or "",
                "natureza_despesa": self.natureza_despesa or "",
                "fonte_recurso": self.fonte_recurso or "",
                "dotacao_id": self.dotacao_id.id if self.dotacao_id else False,
                "processo_id_ref": self.processo_id.id,
                "retroativo": self.retroativo,
                "urgencia": self.urgencia,
                "compras_item_track_id": self.compras_item_track_id.id,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": f"NE - {ne.name}",
            "res_model": "gov.empenho",
            "res_id": ne.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_criar_rascunho(self):
        self.ensure_one()
        if not self.credor_id:
            raise UserError("Informe o credor do empenho.")
        if (self.valor_empenho or 0.0) <= 0:
            raise UserError("Valor do empenho deve ser maior que zero.")

        ne = self.env["gov.empenho"].create(
            {
                "ug_id": self.processo_id.ug_id.id,
                "exercicio": self.exercicio,
                "credor_id": self.credor_id.id,
                "tipo_empenho": self.tipo_empenho,
                "valor_empenho": self.valor_empenho,
                "data_empenho": self.data_empenho,
                "data_vencimento": self.data_vencimento or False,
                "objeto": self.objeto,
                "programa": self.programa or "",
                "acao": self.acao or "",
                "natureza_despesa": self.natureza_despesa or "",
                "fonte_recurso": self.fonte_recurso or "",
                "dotacao_id": self.dotacao_id.id if self.dotacao_id else False,
                "processo_id_ref": self.processo_id.id,
                "retroativo": self.retroativo,
                "urgencia": self.urgencia,
                "compras_item_track_id": self.compras_item_track_id.id,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": f"NE - {ne.name}",
            "res_model": "gov.empenho",
            "res_id": ne.id,
            "view_mode": "form",
            "target": "current",
        }
