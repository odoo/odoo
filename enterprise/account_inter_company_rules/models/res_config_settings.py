from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    intercompany_generate_bills_refund = fields.Boolean(related='company_id.intercompany_generate_bills_refund', readonly=False)
    intercompany_user_id = fields.Many2one(related='company_id.intercompany_user_id', readonly=False, required=True)
    intercompany_purchase_journal_id = fields.Many2one(related='company_id.intercompany_purchase_journal_id', readonly=False)
    intercompany_document_state = fields.Selection(related='company_id.intercompany_document_state', readonly=False)
