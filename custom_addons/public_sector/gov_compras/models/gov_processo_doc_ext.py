from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovProcessoDoc(models.Model):
    _inherit = "gov.processo.doc"

    doc_type = fields.Selection(
        selection_add=[
            ("requisicao", "Requisição de Compras"),
            ("nad", "NAD — Nota de Autorização de Despesa"),
        ],
        ondelete={
            "requisicao": "set default",
            "nad": "set default",
        },
    )
    compras_item_track_ids = fields.Many2many(
        "gov.compras.item.track",
        "gov_processo_doc_compras_track_rel",
        "doc_id",
        "track_id",
        string="IDs de Rastreio",
        domain="[('processo_id', '=', processo_id)]",
        help=(
            "IDs de rastreio dos itens de compras vinculados a este documento. "
            "No DFD este vinculo e opcional; nas demais etapas e obrigatorio."
        ),
    )
    compras_track_display = fields.Char(
        string="Rastreios",
        compute="_compute_compras_track_display",
    )

    @api.depends("compras_item_track_ids.track_id")
    def _compute_compras_track_display(self):
        for rec in self:
            codes = rec.compras_item_track_ids.mapped("track_id")
            rec.compras_track_display = ", ".join(codes) if codes else ""

    @api.model_create_multi
    def create(self, vals_list):
        Track = self.env["gov.compras.item.track"]
        for vals in vals_list:
            processo_id = vals.get("processo_id")
            doc_type = vals.get("doc_type") or "dfd"
            if processo_id and doc_type != "dfd" and not vals.get("compras_item_track_ids"):
                tracks = Track.search([("processo_id", "=", processo_id)], order="id asc")
                if tracks:
                    vals["compras_item_track_ids"] = [(6, 0, tracks.ids)]
        return super().create(vals_list)

    @api.constrains("processo_id", "doc_type", "compras_item_track_ids")
    def _check_compras_track_ids_por_etapa(self):
        for rec in self:
            if not rec.processo_id:
                continue
            if rec.doc_type == "dfd":
                continue

            if not rec.processo_id.compras_item_ids:
                raise ValidationError(
                    "Cadastre ao menos um ID de rastreio na aba Compras do processo antes de criar documentos fora do DFD."
                )
            if not rec.compras_item_track_ids:
                raise ValidationError(
                    "O vinculo de ID de rastreio e obrigatorio para esta etapa do processo. "
                    "Somente no DFD ele e opcional."
                )

            invalid = rec.compras_item_track_ids.filtered(lambda track: track.processo_id != rec.processo_id)
            if invalid:
                raise ValidationError(
                    "Existe ID de rastreio de outro processo no documento atual. "
                    "Use apenas rastreios pertencentes ao mesmo processo."
                )
