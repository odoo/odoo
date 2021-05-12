# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IncomingMessage(models.Model):
    """Technical model that stores the incoming emails which are not routed or create alias.

    The purpose of this model is to detect loop (e.g.: a auto-replier which send email
    to Odoo and Odoo might send auto-reply to those emails).

    This table is cleaned automatically to avoid to store a huge amount of records over time.
    """

    _name = 'mail.incoming.message'
    _description = 'Incoming Message'
    _order = 'id desc'
    _rec_name = 'subject'

    subject = fields.Char('Subject')
    email_from = fields.Char('From')
    email_to = fields.Char('To')

    is_routed = fields.Boolean('Is Routed', default=True)
    alias_model = fields.Char('Created Alias Model', help='Alias model if the message created a record')

    @api.autovacuum
    def _gc_incoming_message(self):
        """Remove incoming messages not needed for loop detection."""
        INCOMING_LIMIT_PERIOD = int(self.env["ir.config_parameter"].sudo().get_param("mail.incoming.limit.period", 60))

        mail_incoming_messages = self.sudo().search([
            ('create_date', '<', datetime.now() - timedelta(minutes=INCOMING_LIMIT_PERIOD)),
        ])

        if mail_incoming_messages:
            _logger.info('Remove %i <mail.incoming.message>', len(mail_incoming_messages))
            mail_incoming_messages.unlink()
