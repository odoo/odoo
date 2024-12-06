# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import string

from odoo import api, fields, models


class MailingTrace(models.Model):
    """ Improve statistics model to add SMS support. Main attributes of
    statistics model are used, only some specific data is required. """
    _inherit = 'mailing.trace'
    CODE_SIZE = 3

    trace_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})
    sms_id = fields.Many2one('sms.sms', string='SMS', store=False, compute='_compute_sms_id')
    sms_id_int = fields.Integer(
        string='SMS ID',
        index='btree_not_null'
        # Integer because the related sms.sms can be deleted separately from its statistics.
        # However, the ID is needed for several action and controllers.
    )
    sms_tracker_ids = fields.One2many('sms.tracker', 'mailing_trace_id', string='SMS Trackers')
    sms_number = fields.Char('Number')
    sms_code = fields.Char('Code')
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_country_not_supported', 'Country Not Supported'),
        ('sms_registration_needed', 'Country-specific Registration Required'),
        ('sms_server', 'Server Error'),
        ('sms_acc', 'Unregistered Account'),
        # mass mode specific codes
        ('sms_blacklist', 'Blacklisted'),
        ('sms_duplicate', 'Duplicate'),
        ('sms_optout', 'Opted Out'),
        # delivery report errors
        ('sms_expired', 'Expired'),
        ('sms_invalid_destination', 'Invalid Destination'),
        ('sms_not_allowed', 'Not Allowed'),
        ('sms_not_delivered', 'Not Delivered'),
        ('sms_rejected', 'Rejected'),
    ])

    @api.depends('sms_id_int', 'trace_type')
    def _compute_sms_id(self):
        self.sms_id = False
        sms_traces = self.filtered(lambda t: t.trace_type == 'sms' and bool(t.sms_id_int))
        if not sms_traces:
            return
        existing_sms_ids = self.env['sms.sms'].sudo().search([
            ('id', 'in', sms_traces.mapped('sms_id_int')), ('to_delete', '!=', True)
        ]).ids
        for sms_trace in sms_traces.filtered(lambda n: n.sms_id_int in set(existing_sms_ids)):
            sms_trace.sms_id = sms_trace.sms_id_int

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if values.get('trace_type') == 'sms' and not values.get('sms_code'):
                values['sms_code'] = self._get_random_code()
        return super(MailingTrace, self).create(values_list)

    def _get_random_code(self):
        """ Generate a random code for trace. Uniqueness is not really necessary
        as it serves as obfuscation when unsubscribing. A valid trio
        code / mailing_id / number will be requested. """
        return ''.join(random.choice(string.ascii_letters + string.digits) for dummy in range(self.CODE_SIZE))
