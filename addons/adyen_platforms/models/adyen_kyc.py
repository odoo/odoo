# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


ADYEN_KYC_STATUS = [
    ('awaiting_data', 'Data To Provide'),
    ('pending', 'Waiting For Validation'),
    ('data_provided', 'Data Provided'),
    ('passed', 'Confirmed'),
    ('failed', 'Failed'),
]

class AdyenKYC(models.Model):
    _name = 'adyen.kyc'
    _description = 'Adyen KYC checks'

    status_message = fields.Char()
    status = fields.Selection(string='KYC Status', selection=[
        ('awaiting_data', 'Data To Provide'),
        ('pending', 'Waiting For Validation'),
        ('data_provided', 'Data Provided'),
        ('passed', 'Confirmed'),
        ('failed', 'Failed'),
    ], required=True, default='pending')

    adyen_account_id = fields.Many2one('adyen.account', required=True, ondelete='cascade')
    bank_account_id = fields.Many2one(
        'adyen.bank.account', domain="[('adyen_account_id', '=', adyen_account_id)]", ondelete='cascade')
    shareholder_id = fields.Many2one(
        'adyen.shareholder', domain="[('adyen_account_id', '=', adyen_account_id)]", ondelete='cascade')
    document = fields.Char(compute='_compute_document')

    verification_type = fields.Selection([
        ('company', 'Company'),
        ('identity', 'Identity'),
        ('passport', 'Passport'),
        ('bank_account', 'Bank Account'),
        ('nonprofit', 'Nonprofit'),
        ('card', 'Card'),
    ], string='KYC Document')

    last_update = fields.Datetime(string="Last Update")

    def _sort_by_status(self):
        order = ['failed', 'awaiting_data', 'pending', 'data_provided', 'passed']
        kyc_sorted = sorted(self, key=lambda k: order.index(k.status))
        return kyc_sorted

    @api.depends('bank_account_id', 'shareholder_id')
    def _compute_document(self):
        self.document = False
        for kyc in self.filtered(lambda k: k.bank_account_id or k.shareholder_id):
            kyc.document = kyc.bank_account_id.display_name or kyc.shareholder_id.display_name
