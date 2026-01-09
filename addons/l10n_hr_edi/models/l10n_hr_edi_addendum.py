from odoo import models, fields


class L10nHrEdiAddendum(models.Model):
    _name = 'l10n_hr_edi.addendum'
    _description = 'EDI and fiscalization information for Croatian electronic invoicing'

    move_id = fields.Many2one('account.move', required=True, ondelete='cascade', index=True)

    # EDI and fiscalization-specific fields
    invoice_sending_time = fields.Datetime(string="Time of invoicing")
    business_document_status = fields.Selection(
        selection=[
            ('0', 'APPROVED'),
            ('1', 'REJECTED'),
            ('2', 'PAYMENT_FULFILLED'),
            ('3', 'PAYMENT_PARTIALLY_FULLFILLED'),
            ('4', 'RECEIVING_CONFIRMED'),
            ('99', 'RECEIVED'),
            ('None', 'None')
        ],
        string='Business document status',
    )
    business_status_reason = fields.Char(
        string='Document rejection reason',
        default='None',
    )
    fiscalization_number = fields.Char(
        string='Invoice fiscalization number',
    )
    fiscalization_status = fields.Selection(
        selection=[
            ('0', "Successful"),
            ('1', "Unsuccessful"),
            ('2', "Pending"),
        ],
        string='Fiscalization status',
    )
    fiscalization_error = fields.Char(
        string='Error reported for fiscalization',
        default='None',
    )
    fiscalization_request = fields.Char(
        string='Fiscalization request ID',
    )
    fiscalization_channel_type = fields.Selection(
        selection=[
            ('0', "Delivered via EDI"),
            ('1', "Not delivered via EDI"),
        ],
        string='Delivery channel type',
        help="If delivery via EDI fails, the invoice is reported to tax authorities but has to be delivered to the client via other means (ex. e-mail)."
    )
    # Payment reporting
    currency_id = fields.Many2one(related='move_id.currency_id')
    payment_reported_amount = fields.Monetary(
        string="Payment amount already reported to Tax Authority",
        currency_field='currency_id',
        default=0.0,
    )
    payment_method_type = fields.Selection(
        selection=[
            ('T', 'Transakcijski račun'),  # Bank account
            ('O', 'Obračunsko plaćanje'),  # Settlement payment
            ('Z', 'Ostalo'),               # Other
        ],
        string='Payment Method Type',
        default='T',
    )
    # MojEracun integration fields
    mer_document_eid = fields.Char(string='MojEracun document ElectronicId')
    mer_document_status = fields.Selection(
        selection=[
            ('20', 'In validation'),
            ('30', 'Sent'),
            ('40', 'Delivered'),
            ('45', 'Canceled'),
            ('50', 'Unsuccessful'),
            ('70', 'Delivered (eReporting)'),
        ],
        string='MojEracun document status',
        help="MojEracun internal document status - to be validated and received by the customer.",
    )
    mer_signed_xml_archived = fields.Boolean(string='Signed XML archived')
