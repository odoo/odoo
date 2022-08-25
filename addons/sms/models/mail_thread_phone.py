# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PhoneMixin(models.AbstractModel):
    _inherit = 'mail.thread.phone'

    def _sms_get_number_fields(self):
        """ Add fields coming from mail.thread.phone implementation. """
        phone_fields = self._phone_get_number_fields()
        sms_fields = super(PhoneMixin, self)._sms_get_number_fields()
        for fname in (f for f in sms_fields if f not in phone_fields):
            phone_fields.append(fname)
        return phone_fields
