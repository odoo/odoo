# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _sms_get_default_partners(self):
        """ Override of mail.thread method.
            SMS recipients on partners are the partners themselves.
        """
        return self
