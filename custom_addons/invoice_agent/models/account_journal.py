from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    ai_agent_enabled = fields.Boolean(
        string='AI Agent Enabled',
        default=False,
        help="Enable the AI extraction agent for bills posted to this journal.",
    )
    ai_min_confidence = fields.Float(
        string='AI Min Confidence',
        default=0.75,
        digits=(3, 2),
        help="Minimum confidence score (0.00–1.00) required for automatic validation. "
             "Used as the variance threshold and the constraint floor.",
    )
    ai_auto_post = fields.Boolean(
        string='AI Auto Post',
        default=False,
        help="Automatically post invoice when AI extraction confidence meets the minimum threshold.",
    )
