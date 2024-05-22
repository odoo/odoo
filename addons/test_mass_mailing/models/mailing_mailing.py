# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Mailing(models.Model):
    _inherit = 'mailing.mailing'

    def _get_opt_out_list(self):
        """Returns a set of emails opted-out in target model"""
        self.ensure_one()
        if self.mailing_model_real == 'mailing.test.optout':
            res_ids = self._get_recipients()
            opt_out_contacts = set(self.env['mailing.test.optout'].search([
                ('id', 'in', res_ids),
                ('opt_out', '=', True)
            ]).mapped('email_normalized'))
            _logger.info(
                "Mass-mailing %s targets %s, optout: %s emails",
                self, self.mailing_model_real, len(opt_out_contacts))
            return opt_out_contacts
        return super(Mailing, self)._get_opt_out_list()
