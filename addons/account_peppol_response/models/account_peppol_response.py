from odoo import fields, models


class AccountPeppolResponse(models.Model):
    _name = 'account.peppol.response'
    _description = 'Business Level Responses for Peppol'

    peppol_message_uuid = fields.Char('Peppol UUID')
    response_code = fields.Selection(
        selection=[
            ('AB', 'Acknowledgement'),
            ('IP', 'In Process'),
            ('UQ', 'Under query'),
            ('CA', 'Conditionally accepted'),
            ('RE', 'Rejection'),
            ('AP', 'Approval'),
            ('PD', 'Paid'),
        ], required=True,
    )
    peppol_state = fields.Selection(
        selection=[
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('not_serviced', 'Not Serviced'),
        ],
        string='Peppol status',
    )
    move_id = fields.Many2one('account.move', ondelete='cascade')
    company_id = fields.Many2one(related='move_id.company_id')
