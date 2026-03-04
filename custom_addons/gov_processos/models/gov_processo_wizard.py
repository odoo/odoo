from odoo import api, fields, models

from .constants import PROCESS_SCOPE_SELECTION, PROCESS_TYPE_SELECTION


class GovProcessoWizard(models.TransientModel):
    _name = "gov.processo.wizard"
    _description = "Criação Rápida de Processo"

    subject = fields.Char(string="Objeto / Assunto", required=True)
    origin_type = fields.Selection(
        selection=[
            ("dfd", "DFD — Formalização de Demanda"),
            ("oficio", "Ofício / Memorando Interno"),
            ("externo", "Provocação Externa (TCE, MPE, Cidadão)"),
            ("despacho", "Despacho de Autoridade"),
            ("ne_indenizatoria", "NE Indenizatória (retroativo)"),
            ("os_urgencia", "Ordem de Serviço de Urgência"),
        ],
        string="Origem",
        required=True,
        default="dfd",
    )
    process_type = fields.Selection(
        selection=PROCESS_TYPE_SELECTION,
        string="Tipo de Processo",
        required=True,
        default="compras_servicos",
    )
    process_scope = fields.Selection(
        selection=PROCESS_SCOPE_SELECTION,
        string="Escopo",
        required=True,
        default="compras",
        help="Segregação AGU: compras, serviços ou serviços de prestação continuada.",
    )
    recommended_template_ids = fields.Many2many(
        "gov.ai.template",
        string="Modelos e Checklists Recomendados",
        compute="_compute_recommended_templates",
        compute_sudo=True,
    )
    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsável",
        default=lambda self: self.env.user,
    )

    @api.model
    def _get_template_scope_values(self, scope):
        scope = scope or "compras"
        if scope == "servicos_continuados":
            return ["all", "servicos", "servicos_continuados"]
        return ["all", scope]

    @api.model
    def _get_template_scope_priority(self, selected_scope, template_scope):
        if template_scope == "all":
            return 0
        if selected_scope == "servicos_continuados":
            if template_scope == "servicos":
                return 1
            if template_scope == "servicos_continuados":
                return 2
            return -1
        if template_scope == selected_scope:
            return 2
        return -1

    @api.model
    def _refine_recommended_templates(self, templates, selected_scope):
        checklists = templates.filtered("is_checklist")
        if not checklists:
            return templates

        max_priority = max(
            self._get_template_scope_priority(selected_scope, checklist.process_scope)
            for checklist in checklists
        )
        if max_priority <= 0:
            return templates

        selected_checklist_ids = set(
            checklists.filtered(
                lambda checklist: self._get_template_scope_priority(
                    selected_scope, checklist.process_scope
                )
                == max_priority
            ).ids
        )
        return templates.filtered(
            lambda template: not template.is_checklist or template.id in selected_checklist_ids
        )

    @api.depends("process_type", "process_scope")
    def _compute_recommended_templates(self):
        Template = self.env["gov.ai.template"].sudo()
        for wizard in self:
            if not wizard.process_type:
                wizard.recommended_template_ids = Template.browse()
                continue
            scope = wizard.process_scope or "compras"
            scope_values = wizard._get_template_scope_values(scope)
            wizard.recommended_template_ids = Template.search(
                [
                    ("active", "=", True),
                    ("process_type", "=", wizard.process_type),
                    ("process_scope", "in", scope_values),
                ],
                order="is_checklist desc, process_scope, fase asc, id asc",
            )
            wizard.recommended_template_ids = wizard._refine_recommended_templates(
                wizard.recommended_template_ids,
                scope,
            )

    def action_criar_processo(self):
        self.ensure_one()
        processo = self.env["gov.processo"].create(
            {
                "subject": self.subject,
                "origin_type": self.origin_type,
                "process_type": self.process_type,
                "process_scope": self.process_scope,
                "ug_id": self.ug_id.id,
                "responsible_id": self.responsible_id.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.processo",
            "res_id": processo.id,
            "view_mode": "form",
            "target": "current",
        }
