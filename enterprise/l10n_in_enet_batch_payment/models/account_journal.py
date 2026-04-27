from odoo import api, Command, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    bank_template_id = fields.Many2one('enet.bank.template', string='Bank Template')
    enet_template_field_ids = fields.One2many('enet.template', 'journal_id', compute='_compute_enet_template_field_ids', store=True)
    has_enet_payment_method = fields.Boolean(compute='_compute_has_enet_payment_method')

    @api.depends('outbound_payment_method_line_ids.payment_method_id.code')
    def _compute_has_enet_payment_method(self):
        for journal in self:
            journal.has_enet_payment_method = any(
                payment_method.payment_method_id.code in ['enet_rtgs', 'enet_neft', 'enet_fund_transfer', 'enet_demand_draft']
                for payment_method in journal.outbound_payment_method_line_ids
            )

    @api.depends('bank_template_id')
    def _compute_enet_template_field_ids(self):
        for journal in self:
            bank_template = journal.bank_template_id
            if bank_template:
                journal.enet_template_field_ids = [Command.clear()] + [
                    Command.create({**field, 'journal_id': journal.id}) for field in bank_template.bank_configuration]
            else:
                journal.enet_template_field_ids = False
