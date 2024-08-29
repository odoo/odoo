# -*- coding: utf-8 -*-
from odoo.addons import point_of_sale
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class POSOrder(models.Model, point_of_sale.PosOrder):

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.company_id.country_id.code == 'SA':
            vals.update({'l10n_sa_confirmation_datetime': self.date_order})
        return vals
