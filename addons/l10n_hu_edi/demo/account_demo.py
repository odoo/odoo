# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import time

import logging

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    # @api.model
    # def _get_demo_data(self):
    #     ref = self.env.ref
    #
    #     yield ('res.partner', {
    #         'base.res_partner_12': {
    #             'vat': "",
    #         },
    #         'base.res_partner_2': {
    #             'vat': "",
    #         },
    #     })
    #     for model, data in super()._get_demo_data():
    #         yield model, data

    @api.model
    def _get_demo_data_move(self):
        if self.env.company.account_fiscal_country_id.code != "HU":
            return super()._get_demo_data_move()

        cid = self.env.company.id
        ref = self.env.ref

        cash_rounding = self.env["account.cash.rounding"].search([
            ("rounding", "=", 1.00),
            ("strategy", "=", "add_invoice_line"),
            ("profit_account_id", "!=", False),
            ("profit_account_id.company_id", "=", cid),
        ], limit=1)

        model, data = super()._get_demo_data_move()
        data[f"{cid}_demo_invoice_1"].update(
            {
                # "partner_id": ref("l10n_hu_edi.res_partner_hu_01").id,
                "l10n_hu_delivery_date": time.strftime("%Y-%m-01"),
                "invoice_cash_rounding_id": cash_rounding.id,
            }
        )
        data[f"{cid}_demo_invoice_2"].update(
            {
                "partner_id": ref("l10n_hu_edi.res_partner_hu_01").id,
                "l10n_hu_delivery_date": time.strftime("%Y-%m-05"),
                "invoice_cash_rounding_id": cash_rounding.id,
            }
        )
        data[f"{cid}_demo_invoice_3"].update(
            {
                "partner_id": ref("l10n_hu_edi.res_partner_hu_01").id,
                "l10n_hu_delivery_date": time.strftime("%Y-%m-05"),
                "invoice_cash_rounding_id": cash_rounding.id,
            }
        )
        data[f"{cid}_demo_invoice_followup"].update(
            {
                "partner_id": ref("l10n_hu_edi.res_partner_hu_01").id,
                "l10n_hu_delivery_date": data[f"{cid}_demo_invoice_followup"]["invoice_date"],
                "invoice_cash_rounding_id": cash_rounding.id,
            }
        )
        data[f"{cid}_demo_invoice_5"].update(
            {
                "partner_id": ref("l10n_hu_edi.res_partner_hu_01").id,
                "invoice_cash_rounding_id": cash_rounding.id,
            }
        )

        # data[f'{cid}_demo_invoice_equipment_purchase']['l10n_latam_document_number'] = '1-2'
        return model, data
