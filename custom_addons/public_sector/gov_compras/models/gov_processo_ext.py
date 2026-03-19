from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError


class GovProcesso(models.Model):
    _inherit = "gov.processo"

    compras_item_ids = fields.One2many(
        "gov.compras.item.track",
        "processo_id",
        string="Itens de Compras",
    )
    compras_item_count = fields.Integer(
        string="Qtd. Itens Compras",
        compute="_compute_compras_item_count",
    )

    @api.depends("compras_item_ids")
    def _compute_compras_item_count(self):
        for rec in self:
            rec.compras_item_count = len(rec.compras_item_ids)

    def action_open_compras_itens(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Itens de Compras",
            "res_model": "gov.compras.item.track",
            "view_mode": "list,form",
            "domain": [("processo_id", "=", self.id)],
            "context": {
                "default_processo_id": self.id,
            },
        }

    def _create_doc_compras(self, doc_type, title, html, tracks=None):
        self.ensure_one()
        vals = {
            "processo_id": self.id,
            "doc_type": doc_type,
            "name": title,
            "content_html": html,
        }
        if tracks:
            vals["compras_item_track_ids"] = [(6, 0, tracks.ids)]
        doc = self.env["gov.processo.doc"].create(vals)
        return doc

    def action_compras_enviar_requisicao(self):
        for rec in self:
            tracks = rec.compras_item_ids.filtered(lambda x: x.status == "rascunho")
            if not tracks:
                raise UserError("Não há itens em rascunho para enviar como requisição.")
            tracks.write({"status": "requisitado"})
            html = "<h3>Requisição de Compras</h3><ul>"
            for line in tracks:
                html += f"<li>{line.track_id} - {line.catalog_item_id.name}: {line.quantidade:g} {line.unidade_medida or 'UN'}</li>"
            html += "</ul>"
            doc = rec._create_doc_compras(
                "requisicao",
                f"Requisição de Compras - {rec.name}",
                html,
                tracks=tracks,
            )
            rec.message_post(
                body=Markup(
                    f"🧾 <b>Requisição emitida.</b> Documento criado: <b>{doc.name}</b>."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

    def action_compras_aprovar_requisicao(self):
        for rec in self:
            tracks = rec.compras_item_ids.filtered(lambda x: x.status == "requisitado")
            if not tracks:
                raise UserError("Não há requisições pendentes para aprovar.")
            tracks.write({"status": "nad"})
            html = "<h3>Nota de Autorização de Despesa (NAD)</h3><ul>"
            for line in tracks:
                ref = line.valor_estimado_ref or line.preco_referencia_conservador or 0.0
                html += (
                    f"<li>{line.track_id} - {line.catalog_item_id.name}: "
                    f"{line.quantidade:g} x {ref:.2f}</li>"
                )
            html += "</ul>"
            doc = rec._create_doc_compras(
                "nad",
                f"NAD - {rec.name}",
                html,
                tracks=tracks,
            )
            rec.message_post(
                body=Markup(
                    f"✅ <b>Requisição aprovada.</b> NAD criada: <b>{doc.name}</b>."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
