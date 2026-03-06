from markupsafe import Markup

from odoo import fields, models

from .gov_processo_tramite import TRAMITE_ACTION_SELECTION


class GovProcessoTramiteWizard(models.TransientModel):
    _name = "gov.processo.tramite.wizard"
    _description = "Wizard de Tramitação"

    processo_id = fields.Many2one(
        "gov.processo",
        required=True,
        readonly=True,
    )
    from_ug_id = fields.Many2one(
        "res.company",
        string="UG de Origem",
        default=lambda self: self.env.company,
        readonly=True,
    )
    to_ug_id = fields.Many2one(
        "res.company",
        string="UG de Destino",
    )
    action = fields.Selection(
        selection=TRAMITE_ACTION_SELECTION,
        required=True,
        default="despacho",
    )
    note = fields.Text(string="Observação / Despacho")
    prazo_dias = fields.Integer(string="Prazo (dias úteis)")

    def action_confirmar(self):
        self.ensure_one()
        tramite = self.env["gov.processo.tramite"].with_context(skip_tramite_chatter=True).create(
            {
                "processo_id": self.processo_id.id,
                "from_ug_id": self.from_ug_id.id,
                "to_ug_id": self.to_ug_id.id if self.to_ug_id else False,
                "action": self.action,
                "note": self.note,
                "prazo_dias": self.prazo_dias,
            }
        )

        action_label = dict(self.env["gov.processo.tramite"]._fields["action"].selection).get(
            self.action, self.action
        )
        destino = self.to_ug_id.name if self.to_ug_id else "mesma UG"
        msg = f"<b>{action_label}</b> por {self.env.user.name}<br/>Para: {destino}"
        if self.note:
            msg += f"<br/>Observação: {self.note}"
        if self.prazo_dias:
            msg += f"<br/>Prazo: {self.prazo_dias} dias úteis"

        self.processo_id.message_post(
            body=Markup(msg),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        if self.to_ug_id and self.to_ug_id != self.from_ug_id:
            responsaveis = self.env["res.users"].search(
                [
                    ("company_id", "=", self.to_ug_id.id),
                    ("group_ids", "in", [self.env.ref("gov_base.group_gov_operador").id]),
                ]
            )
            if responsaveis:
                partner_ids = responsaveis.mapped("partner_id").ids
                self.processo_id.message_subscribe(partner_ids=partner_ids)
                self.processo_id.message_post(
                    body=Markup(f"Processo encaminhado para {destino}. Por favor, verifique."),
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                    partner_ids=partner_ids,
                )

        if not tramite:
            return {"type": "ir.actions.act_window_close"}
        return {"type": "ir.actions.act_window_close"}
