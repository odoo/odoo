# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import string

from odoo import api, fields, models
from odoo.osv import expression


class MailingTrace(models.Model):
    """ Improve statistics model to add SMS support. Main attributes of
    statistics model are used, only some specific data is required. """
    _inherit = 'mailing.trace'
    CODE_SIZE = 3

    trace_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})
    sms_sms_id = fields.Many2one('sms.sms', string='SMS', index='btree_not_null', ondelete='set null')
    sms_sms_id_int = fields.Integer(
        string='SMS ID (tech)',
        index='btree_not_null'
        # Integer because the related sms.sms can be deleted separately from its statistics.
        # However the ID is needed for several action and controllers.
    )
    sms_uuid = fields.Char(
        string='UUID',
        help='UUID for identifying messages',
        compute='_compute_uuid',
        store=True,
        index=True,
    )
    sms_number = fields.Char('Number')
    sms_code = fields.Char('Code')
    trace_status = fields.Selection(selection_add=[
        ('processing', 'Processing'),
    ], ondelete={'processing': 'cascade'})
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error'),
        ('sms_acc', 'Unregistered Account'),
        # mass mode specific codes
        ('sms_blacklist', 'Blacklisted'),
        ('sms_duplicate', 'Duplicate'),
        ('sms_optout', 'Opted Out'),
        # delivery report errors (DLR)
        ('sms_not_delivered', 'Not Delivered'),
        ('sms_not_allowed', 'Not Allowed'),
        ('sms_invalid_destination', 'Invalid Destination'),
        ('sms_rejected', 'Rejected'),
        ('sms_expired', 'Expired'),
    ])

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'sms_sms_id' in values:
                values['sms_sms_id_int'] = values['sms_sms_id']
            if values.get('trace_type') == 'sms' and not values.get('sms_code'):
                values['sms_code'] = self._get_random_code()
        return super(MailingTrace, self).create(values_list)

    @api.depends('sms_sms_id')
    def _compute_uuid(self):
        for record in self:
            if record.sms_sms_id:
                record.sms_uuid = record.sms_sms_id.uuid

    def _get_random_code(self):
        """ Generate a random code for trace. Uniqueness is not really necessary
        as it serves as obfuscation when unsubscribing. A valid trio
        code / mailing_id / number will be requested. """
        return ''.join(random.choice(string.ascii_letters + string.digits) for dummy in range(self.CODE_SIZE))

    def update_status(self, sms_status):
        if sms_status in {'delivered', 'sent', 'not_delivered'}:
            self.set_sent()
        else:
            self.write({
                'trace_status': 'error',
                'failure_type': self.env['sms.sms'].IAP_TO_SMS_STATE.get(sms_status)
            })
