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

    trace_type = fields.Selection(selection_add=[('sms', 'SMS')])
    sms_id = fields.Many2one('sms.sms', string='SMS', index=True, ondelete='set null')
    sms_id_int = fields.Integer(
        string='SMS ID (tech)',
        help='ID of the related sms.sms. This field is an integer field because '
             'the related sms.sms can be deleted separately from its statistics. '
             'However the ID is needed for several action and controllers.',
        index=True,
    )
    sms_number = fields.Char('Number')
    sms_code = fields.Char('Code')
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error'),
        # mass mode specific codes
        ('sms_blacklist', 'Blacklisted'),
        ('sms_duplicate', 'Duplicate'),
    ])

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'sms_id' in values:
                values['sms_id_int'] = values['sms_id']
            if values.get('trace_type') == 'sms' and not values.get('sms_code'):
                values['sms_code'] = self._get_random_code()
        return super(MailingTrace, self).create(values_list)

    def _get_random_code(self):
        """ Generate a random code for trace. Uniqueness is not really necessary
        as it serves as obfuscation when unsubscribing. A valid trio
        code / mailing_id / number will be requested. """
        return ''.join(random.choice(string.ascii_letters + string.digits) for dummy in range(self.CODE_SIZE))

    def _get_records_from_sms(self, sms_ids=None, additional_domain=None):
        if not self.ids and sms_ids:
            domain = [('sms_id_int', 'in', sms_ids)]
        else:
            domain = [('id', 'in', self.ids)]
        if additional_domain:
            domain = expression.AND([domain, additional_domain])
        return self.search(domain)

    def set_failed(self, failure_type):
        for trace in self:
            trace.write({'exception': fields.Datetime.now(), 'failure_type': failure_type})

    def set_sms_sent(self, sms_ids=None):
        statistics = self._get_records_from_sms(sms_ids, [('sent', '=', False)])
        statistics.write({'sent': fields.Datetime.now()})
        return statistics

    def set_sms_clicked(self, sms_ids=None):
        statistics = self._get_records_from_sms(sms_ids, [('clicked', '=', False)])
        statistics.write({'clicked': fields.Datetime.now()})
        return statistics

    def set_sms_canceled(self, sms_ids=None):
        statistics = self._get_records_from_sms(sms_ids, [('canceled', '=', False)])
        statistics.write({'canceled': fields.Datetime.now()})
        return statistics

    def set_sms_exception(self, sms_ids=None):
        statistics = self._get_records_from_sms(sms_ids, [('exception', '=', False)])
        statistics.write({'exception': fields.Datetime.now()})
        return statistics
