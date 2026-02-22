from odoo import fields, models


class PdpPaymentEvent(models.Model):
    _name = 'l10n.fr.pdp.payment.event'
    _description = 'PDP Payment Event'
    _order = 'event_date asc, id asc'

    move_id = fields.Many2one(
        comodel_name='account.move',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
    )
    payment_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Payment Move',
    )
    source_partial_id = fields.Integer(index=True)
    event_date = fields.Date(required=True, index=True)
    amount = fields.Monetary(currency_field='currency_id', required=True)
    state = fields.Selection(
        selection=[('pending', 'Pending'), ('reported', 'Reported')],
        default='pending',
        required=True,
        index=True,
    )
    reported_flow_id = fields.Many2one(
        comodel_name='l10n.fr.pdp.flow',
        ondelete='set null',
    )

    _sql_constraints = [
        (
            'l10n_fr_pdp_payment_event_partial_move_uniq',
            'unique(source_partial_id, move_id)',
            'A payment event for this partial reconciliation and invoice already exists.',
        ),
    ]
