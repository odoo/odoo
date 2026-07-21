from odoo import fields, models


class NemhandelResponse(models.Model):
    _name = 'nemhandel.response'
    _description = 'Business Level Responses for Nemhandel'

    nemhandel_message_uuid = fields.Char('Nemhandel UUID')
    response_code = fields.Selection(
        selection=[
            ('BusinessAccept', 'Approval'),
            ('BusinessReject', 'Rejection'),
        ], required=True,
    )
    nemhandel_state = fields.Selection(
        selection=[
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('not_serviced', 'Not Serviced'),
        ],
        string='Nemhandel status',
    )
    move_id = fields.Many2one('account.move', ondelete='cascade')
    company_id = fields.Many2one(related='move_id.company_id')
