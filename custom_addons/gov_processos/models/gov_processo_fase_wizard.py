from odoo import fields, models
from odoo.exceptions import UserError


class GovProcessoFaseWizard(models.TransientModel):
    _name = "gov.processo.fase.wizard"
    _description = "Wizard de transição de fase"

    processo_id = fields.Many2one("gov.processo", required=True, readonly=True)
    direction = fields.Selection(
        selection=[
            ("avancar", "Avançar"),
            ("retroceder", "Retroceder"),
        ],
        required=True,
        readonly=True,
    )
    justificativa = fields.Text(
        string="Justificativa",
        help="Obrigatória ao retroceder fase.",
    )
    warning_message = fields.Html(
        string="Aviso",
        compute="_compute_warning_message",
        sanitize=False,
    )

    def _compute_warning_message(self):
        for rec in self:
            if rec.direction == "retroceder":
                rec.warning_message = (
                    "<div class='alert alert-warning' role='alert'>"
                    "<strong>Atenção:</strong> o retrocesso de fase exige justificativa "
                    "e ficará registrado no histórico do processo."
                    "</div>"
                )
            else:
                rec.warning_message = (
                    "<div class='alert alert-warning' role='alert'>"
                    "<strong>Atenção:</strong> após avançar a fase, o retorno só pode ser "
                    "feito por gestor, mediante justificativa."
                    "</div>"
                )

    def action_confirmar(self):
        self.ensure_one()
        if self.direction == "retroceder":
            if not self.env.user.has_group("gov_base.group_gov_gestor"):
                raise UserError("Apenas gestores podem retroceder fase.")
            self.processo_id.action_retroceder_fase(self.justificativa or "")
        else:
            self.processo_id.action_avancar_fase()
        return {"type": "ir.actions.act_window_close"}
