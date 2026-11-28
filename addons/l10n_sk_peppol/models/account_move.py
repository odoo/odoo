from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sk_tdd_attachment_id = fields.Many2one(comodel_name='ir.attachment', string='Tax Data Document', copy=False)

    def _get_moves_waiting_for_tdd(self, company):
        if company.routing_scheme != '0245' or not company.vat:
            return self.env['account.move']

        return self.search([
            ('company_id', '=', company.id),
            ('peppol_message_uuid', '!=', False),
            ('partner_id.routing_scheme', '=', '0245'),
            ('partner_id.vat', '!=', False),
            ('l10n_sk_tdd_attachment_id', '=', False),
        ])
