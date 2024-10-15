# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_in.models.res_partner import L10N_IN_GST_TREATMENTS_TYPE


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    l10n_in_gst_treatment = fields.Selection(
        selection=L10N_IN_GST_TREATMENTS_TYPE,
        string="GST Treatment",
        compute="_compute_l10n_in_gst_treatment",
        store=True,
    )

    @api.depends('partner_id')
    def _compute_l10n_in_gst_treatment(self):
        for order in self:
            # set default value as False so CacheMiss error never occurs for this field.
            order.l10n_in_gst_treatment = False
            if order.country_code == 'IN':
                l10n_in_gst_treatment = order.partner_id.l10n_in_gst_treatment
                if not l10n_in_gst_treatment and order.partner_id.country_id and order.partner_id.country_id.code != 'IN':
                    l10n_in_gst_treatment = 'overseas'
                if not l10n_in_gst_treatment:
                    l10n_in_gst_treatment = order.partner_id.vat and 'regular' or 'consumer'
                order.l10n_in_gst_treatment = l10n_in_gst_treatment
