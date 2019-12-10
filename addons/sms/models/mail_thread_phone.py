# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PhoneMixin(models.AbstractModel):
    _inherit = 'mail.thread.phone'

    def _phone_get_number_fields(self):
        """ Add fields coming from sms implementation. """
        sms_fields = self._sms_get_number_fields()
        res = super(PhoneMixin, self)._phone_get_number_fields()
        for fname in (f for f in res if f not in sms_fields):
            sms_fields.append(fname)
        return sms_fields
