# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import sale


class SaleOrder(sale.SaleOrder):
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        """ Exclude by default canceled orders when performing a mass mailing. """
        return [('state', '!=', 'cancel')]
