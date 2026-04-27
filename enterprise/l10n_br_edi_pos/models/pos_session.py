# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from collections import defaultdict

from odoo import models, api
from odoo.tools import partition


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if self.env.company.country_id.code == "BR":
            data += ["l10n_latam.identification.type"]
        return data

    def _accumulate_amounts(self, data):
        """Override. The point of sale re-calculates tax amounts using account.tax records, but these won't be correctly
        configured when using l10n_br_avatax. This replaces the tax amounts used in the closing entry with the amounts
        returned by l10n_br_avatax.

        This makes several assumptions:
        - taxes are always included in price (NFC-e mandates this),
        - tax configuration is not changed from the default created by l10n_br_avatax (e.g., no extra repartition lines),
        - everything uses the BRL currency (enforced by account.external.tax.mixin in l10n_br_avatax),
        - regular invoicing is not supported (enforced by an override on action_pos_order_invoice),
        - refunds are not handled here, they are never electronically invoiced through the POS.
        """

        def get_repartition_line(tax):
            return tax.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == "tax")[0]

        def update_sales(external_sales, order, line, amount):
            # Recreate the 'sales' dictionary. It's the base amount on which taxes are calculated and will also be wrong.
            account = line.product_id.product_tmpl_id.get_product_accounts()["income"]

            tags = []
            for tax in line.tax_ids:
                tags.extend(get_repartition_line(tax).tag_ids.ids)

            sale_key = (
                account.id,
                1,
                tuple(line.tax_ids.ids),
                tuple(tags),
                line.product_id.id if self.config_id.is_closing_entry_by_product else False,
            )

            external_sales[sale_key] = self._update_amounts(
                external_sales[sale_key],
                {
                    "amount": -amount,
                    "amount_converted": -amount,
                },
                order.date_order,
            )
            if self.config_id.is_closing_entry_by_product:
                external_sales[sale_key] = self._update_quantities(external_sales[sale_key], line.qty)

        res = super()._accumulate_amounts(data)
        if not self.config_id.l10n_br_is_nfce:
            return res

        external_taxes = defaultdict(lambda: {"amount": 0.0, "amount_converted": 0.0, "base_amount": 0.0, "base_amount_converted": 0.0})
        external_sales = defaultdict(lambda: {"amount": 0.0, "amount_converted": 0.0})

        edi_orders, failed_orders = partition(lambda order: order.l10n_br_edi_avatax_data, self._get_closed_orders())
        for order in edi_orders:
            data = order.l10n_br_edi_avatax_data

            # Recreate the 'taxes' dictionary using data from Avatax.
            for l10n_br_avatax_code, details in data["summary"]["taxByType"].items():
                tax = order._l10n_br_find_tax_for_l10n_br_avatax_code(l10n_br_avatax_code)

                repartition_line = get_repartition_line(tax)
                tax_key = (
                    repartition_line.account_id.id,
                    repartition_line.id,
                    tuple(repartition_line.tag_ids.ids),
                )

                external_taxes[tax_key] = self._update_amounts(
                    external_taxes[tax_key],
                    {
                        "amount": -details["tax"],
                        "amount_converted": -details["tax"],
                        "base_amount": -details["subtotalTaxable"] + details["tax"],
                    },
                    order.date_order,
                )

            for result_line in data["lines"]:
                update_sales(
                    external_sales,
                    order,
                    self.env["pos.order.line"].browse(result_line["lineCode"]),
                    result_line["lineNetFigure"],
                )

        for order in failed_orders:
            # there will be no taxes for these
            for line in order.lines:
                update_sales(external_sales, order, line, line.price_subtotal_incl)

        res["taxes"] = external_taxes
        res["sales"] = external_sales
        return res
