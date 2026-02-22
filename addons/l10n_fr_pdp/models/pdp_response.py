from odoo import fields, models


class PdpResponse(models.Model):
    _name = 'pdp.response'
    _description = 'Response Messages for PDP'

    pdp_message_uuid = fields.Char('PDP UUID', required=True)
    # TODO: rename to status?
    response_code = fields.Selection(
        selection=[
            ('submitted', 'Submitted'),
            ('received', 'Received'),
            ('made_available', 'Made Available'),
            ('in_hand', 'In Hand'),
            ('approved', 'Approved'),
            ('contested', 'Contested'),
            ('refused', 'Refused'),
            ('payment_sent', 'Payment Sent'),
            ('paid', 'Paid'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        required=True,
    )
    pdp_state = fields.Selection(
        selection=[
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('not_serviced', 'Not Serviced'),
        ],
        string='PDP status',
        required=True,
    )
    status_info = fields.Text()
    issue_date = fields.Datetime(string="Issue Date")
    move_id = fields.Many2one('account.move', ondelete='cascade')
    company_id = fields.Many2one(related='move_id.company_id')
