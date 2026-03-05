from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovEmpenho(models.Model):
    _inherit = "gov.empenho"

    compras_item_track_id = fields.Many2one(
        "gov.compras.item.track",
        string="Item de Compra (Rastreio)",
        ondelete="set null",
    )

    @api.onchange("compras_item_track_id")
    def _onchange_compras_item_track_id(self):
        for rec in self:
            if rec.compras_item_track_id and not rec.processo_id_ref:
                rec.processo_id_ref = rec.compras_item_track_id.processo_id.id

    def _criar_vinculo_item_track(self):
        for rec in self:
            track = rec.compras_item_track_id
            if not track:
                continue
            track.empenho_id = rec.id
            if track.status in ("nad", "licitado"):
                track.status = "empenhado"

    @api.constrains("valor_empenho", "compras_item_track_id")
    def _check_valor_empenho_contra_arremate(self):
        for rec in self:
            track = rec.compras_item_track_id
            if not track or not track.valor_arrematado:
                continue
            if (rec.valor_empenho or 0.0) > track.valor_arrematado:
                raise ValidationError(
                    (
                        f"O valor do empenho ({rec.valor_empenho:.2f}) não pode exceder "
                        f"o valor arrematado do item {track.track_id} ({track.valor_arrematado:.2f})."
                    )
                )

    @api.constrains("processo_id_ref", "compras_item_track_id")
    def _check_vinculo_track_no_processo(self):
        for rec in self:
            if rec.processo_id_ref and not rec.compras_item_track_id:
                raise ValidationError(
                    "Informe o ID de rastreio do item de compras para empenhos vinculados a processo."
                )
            if (
                rec.processo_id_ref
                and rec.compras_item_track_id
                and rec.compras_item_track_id.processo_id.id != rec.processo_id_ref
            ):
                raise ValidationError(
                    "O ID de rastreio selecionado pertence a outro processo."
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._criar_vinculo_item_track()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._criar_vinculo_item_track()
        return res
