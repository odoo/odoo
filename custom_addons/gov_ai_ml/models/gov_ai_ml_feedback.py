from odoo import fields, models


class GovAiMlFeedback(models.Model):
    _name = "gov.ai.ml.feedback"
    _description = "Feedback de Geracao IA"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default="Feedback IA")
    company_id = fields.Many2one("res.company", required=True, index=True)
    processo_id = fields.Many2one("gov.processo", index=True)
    doc_id = fields.Many2one("gov.processo.doc", index=True)
    run_id = fields.Many2one("gov.ai.run", index=True)
    template_id = fields.Many2one("gov.ai.template", index=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True, readonly=True)
    accepted = fields.Boolean(default=False, index=True)
    score_manual = fields.Integer(default=0)
    doc_type = fields.Selection(related="doc_id.doc_type", store=True, readonly=True)
    process_type = fields.Selection(related="doc_id.process_type", store=True, readonly=True)
    process_scope = fields.Selection(related="doc_id.process_scope", store=True, readonly=True)
    notes = fields.Text()

