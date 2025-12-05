import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    selectOrderLine(order, line) {
        super.selectOrderLine(order, line);
        // Ensure the numpadMode should be `price` when the discount line is selected
        if (line?.isDiscountLine) {
            this.numpadMode = "price";
        }
    },
    async applyDiscount(percent, order = this.getOrder()) {
        const lines = order.getOrderlines();
        const product = this.config.discount_product_id;

        if (product === undefined) {
            this.dialog.add(AlertDialog, {
                title: _t("No discount product found"),
                body: _t(
                    "The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."
                ),
            });
            return;
        }
        const tobeRemoved = order.getDiscountLine(); // remove once we successfully create new line

        const discountableLines = lines.filter((line) => line.isGlobalDiscountApplicable());
        const baseLines = discountableLines.map((line) =>
            accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues()
            )
        );
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, order.company_id);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, order.company_id);

        const groupingFunction = (base_line) => ({
            grouping_key: { product_id: product },
            raw_grouping_key: { product_id: product.id },
        });

        const globalDiscountBaseLines = accountTaxHelpers.prepare_global_discount_lines(
            baseLines,
            order.company_id,
            "percent",
            percent,
            {
                computation_key: "global_discount",
                grouping_function: groupingFunction,
            }
        );
        for (const baseLine of globalDiscountBaseLines) {
            const extra_tax_data = accountTaxHelpers.export_base_line_extra_tax_data(baseLine);
            extra_tax_data.discount_percentage = percent;
            const line = await this.addLineToOrder(
                {
                    product_id: baseLine.product_id,
                    price_unit: baseLine.price_unit,
                    qty: baseLine.quantity,
                    tax_ids: [["link", ...baseLine.tax_ids]],
                    product_tmpl_id: baseLine.product_id.product_tmpl_id,
                    extra_tax_data: extra_tax_data,
                },
                order,
                { merge: false }
            );
            if (line) {
                tobeRemoved?.delete();
            }
            this.numpadMode = "price";
        }
    },
});
