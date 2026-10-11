# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import string

from odoo import api, fields, models
from odoo.tools import SQL


class MailingTrace(models.Model):
    """ Improve statistics model to add SMS support. Main attributes of
    statistics model are used, only some specific data is required. """
    _inherit = 'mailing.trace'
    CODE_SIZE = 3

    trace_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})
    sms_id = fields.Many2one('sms.sms', string='SMS', store=False, compute='_compute_sms_id', compute_sql='_compute_sql_sms_id', compute_sudo=True, inverse='_inverse_sms_id')
    sms_id_real = fields.Many2one('sms.sms', string='SMS')
    sms_id_int = fields.Integer(
        string='SMS ID',
        index='btree_not_null',
        store=True,
        compute='_compute_sms_id_int',
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
        ('sms_database_non_active', 'Database non active'),
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
        # twilio specific: to move in bridge module in master
        ('twilio_authentication', 'Authentication Error"'),
        ('twilio_callback', 'Incorrect callback URL'),
        ('twilio_from_missing', 'Missing From Number'),
        ('twilio_from_to', 'From / To identic'),
    ])

    @api.depends('sms_id_real', 'trace_type')
    def _compute_sms_id(self):
        sms_traces = self.filtered(lambda t: t.trace_type == 'sms' and t.sms_id_real and not t.sms_id_real.to_delete)
        (self - sms_traces).sms_id = False
        if not sms_traces:
            return
        for sms_trace in sms_traces:
            sms_trace.sms_id = sms_trace.sms_id_real

    def _compute_sql_sms_id(self, table):
        return SQL("CASE WHEN %s = 'sms' AND %s IS NOT TRUE THEN %s END", table.trace_type, table.sms_id_real.to_delete, table.sms_id_real)

    def _inverse_sms_id(self):
        for trace in self:
            trace.sms_id_real = int(trace.sms_id)

    @api.depends('sms_id_real')
    def _compute_sms_id_int(self):
        for trace in self:
            trace.sms_id_int = trace.sms_id_real.id or trace.sms_id_int

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('trace_type') == 'sms' and not values.get('sms_code'):
                values['sms_code'] = self._get_random_code()
        return super().create(vals_list)

    def _get_random_code(self):
        """ Generate a random code for trace. Uniqueness is not really necessary
        as it serves as obfuscation when unsubscribing. A valid trio
        code / mailing_id / number will be requested. """
        return ''.join(random.choice(string.ascii_letters + string.digits) for dummy in range(self.CODE_SIZE))
