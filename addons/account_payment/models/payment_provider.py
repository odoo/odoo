# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    journal_id = fields.Many2one(
        string="Payment Journal",
        help="The journal in which the successful transactions are posted.",
        comodel_name='account.journal',
        compute='_compute_journal_id',
        store=True,
        check_company=True,
        domain='[("type", "=", "bank")]',
        copy=False,
    )

    #=== COMPUTE METHODS ===#

    @api.depends('code', 'state', 'company_id')
    def _compute_journal_id(self):
        for provider in self:
            if not provider.journal_id:
                provider.journal_id = self.env['account.journal'].search(
                        [
                            ('company_id', '=', provider.company_id.id),
                            ('type', '=', 'bank'),
                        ],
                        limit=1,
                    )
