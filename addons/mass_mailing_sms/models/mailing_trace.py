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
    sms_id = fields.Many2one('sms.sms', string='SMS', store=False, compute='_compute_sms_id', compute_sql='_compute_sql_sms_id', compute_sudo=True)
    sms_id_int = fields.Many2oneReference(
        string='SMS ID',
        index='btree_not_null',
        model_field='sms_id_model',
        # Reference because the related sms.sms can be deleted separately from its statistics.
        # However, the ID is needed for several action and controllers.
    )
    sms_id_model = fields.Char(string='SMS ID Model', compute='_compute_sms_id_model', compute_sql=lambda _self, _table: SQL('%s', 'sms.sms'), compute_sudo=True)
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

    @api.depends('sms_id_int', 'trace_type')
    def _compute_sms_id(self):
        sms_traces = self.filtered(lambda t: t.trace_type == 'sms' and t.sms_id_int)
        (self - sms_traces).sms_id = False
        if not sms_traces:
            return
        existing_sms_ids = set(self.env['sms.sms'].search([
            ('id', 'in', sms_traces.mapped('sms_id_int')), ('to_delete', '!=', True)
        ]).ids)
        for sms_trace in sms_traces:
            sms_trace.sms_id = sms_trace.sms_id_int in existing_sms_ids and sms_trace.sms_id_int

    def _compute_sql_sms_id(self, table):
        comodel = self.env['sms.sms']
        coalias = table._make_alias('sms_id_int', comodel)
        table._query.add_join('LEFT JOIN', coalias, None, SQL(
            "%s = %s AND %s IS NOT TRUE AND %s = 'sms'",
            table.sms_id_int,
            coalias.id,
            coalias.to_delete,
            table.trace_type,
        ))
        return coalias.id

    def _compute_sms_id_model(self):
        self.sms_id_model = 'sms.sms'

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
