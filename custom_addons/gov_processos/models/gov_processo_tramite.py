from markupsafe import Markup

from odoo import api, fields, models


TRAMITE_ACTION_SELECTION = [
    ("recebimento", "Recebimento"),
    ("instrucao", "Instrução"),
    ("despacho", "Despacho"),
    ("envio", "Envio para outra UG"),
    ("devolucao", "Devolução"),
    ("aprovacao", "Aprovação"),
    ("arquivamento", "Arquivamento"),
]


class GovProcessoTramite(models.Model):
    _name = "gov.processo.tramite"
    _description = "Tramitação de Processo Administrativo"
    _order = "date desc, id desc"

    processo_id = fields.Many2one(
        "gov.processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    from_ug_id = fields.Many2one(
        "res.company",
        string="UG de Origem",
        default=lambda self: self.env.company,
    )
    to_ug_id = fields.Many2one(
        "res.company",
        string="UG de Destino",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsável",
        default=lambda self: self.env.user,
        required=True,
    )
    date = fields.Datetime(
        string="Data/Hora",
        default=fields.Datetime.now,
        required=True,
    )
    action = fields.Selection(
        selection=TRAMITE_ACTION_SELECTION,
        string="Ação",
        required=True,
        default="despacho",
    )
    note = fields.Text(string="Observação")
    prazo_dias = fields.Integer(string="Prazo (dias úteis)")
    duration_hours = fields.Float(
        string="Tempo desde anterior (h)",
        compute="_compute_duration",
        store=True,
    )

    @api.depends("date", "processo_id")
    def _compute_duration(self):
        for rec in self:
            anterior = self.search(
                [
                    ("processo_id", "=", rec.processo_id.id),
                    ("date", "<", rec.date),
                    ("id", "!=", rec.id),
                ],
                order="date desc",
                limit=1,
            )
            if anterior and rec.date:
                delta = rec.date - anterior.date
                rec.duration_hours = round(delta.total_seconds() / 3600, 2)
            else:
                rec.duration_hours = 0.0

    def _message_body(self):
        self.ensure_one()
        action_label = dict(self._fields["action"].selection).get(self.action, self.action)
        destino = self.to_ug_id.name if self.to_ug_id else "mesma UG"
        msg = f"<b>{action_label}</b> por {self.user_id.name}<br/>Para: {destino}"
        if self.note:
            msg += f"<br/>Observação: {self.note}"
        if self.prazo_dias:
            msg += f"<br/>Prazo: {self.prazo_dias} dias úteis"
        return Markup(msg)

    def _post_chatter_message(self):
        for rec in self:
            rec.processo_id.message_post(
                body=rec._message_body(),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("skip_tramite_chatter"):
            records._post_chatter_message()
        return records
