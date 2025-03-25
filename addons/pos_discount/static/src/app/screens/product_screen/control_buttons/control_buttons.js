import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        this.dialog.add(NumberPopup, {
            title: _t("Discount Percentage"),
            startingValue: this.pos.config.discount_pc,
            getPayload: (num) => {
                const percent = Math.max(
                    0,
                    Math.min(100, this.env.utils.parseValidFloat(num.toString()))
                );
                this.applyDiscount(percent);
            },
        });
    },
    // FIXME business method in a compoenent, maybe to move in pos_store
    async applyDiscount(percent) {
        const order = this.pos.getOrder();
        const lines = order.getOrderlines();
        const product = this.pos.config.discount_product_id;

        if (product === undefined) {
            this.dialog.add(AlertDialog, {
                title: _t("No discount product found"),
                body: _t(
                    "The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."
                ),
            });
            return;
        }
        // Remove existing discounts
        lines.filter((line) => line.getProduct() === product).forEach((line) => line.delete());

        const discountableLines = lines.filter((line) => line.isGlobalDiscountApplicable());
        const baseLines = discountableLines.map((line) =>
            line.prepareBaseLineForTaxesComputationExtraValues()
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
            await this.pos.addLineToCurrentOrder(
                {
                    product_id: baseLine.product_id,
                    price_unit: baseLine.price_unit,
                    qty: baseLine.quantity,
                    tax_ids: [["link", ...baseLine.tax_ids]],
                    product_tmpl_id: baseLine.product_id.product_tmpl_id,
                    extra_tax_data: accountTaxHelpers.export_base_line_extra_tax_data(baseLine),
                },
                { merge: false }
            );
        }
    },
});
