import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";
import { PosOrderAccounting } from "@point_of_sale/app/models/accounting/pos_order_accounting";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.debouncedDiscount = debounce(this.applyDiscount.bind(this));

        const updateOrderDiscount = (order) => {
            if (!order || order.state !== "draft") {
                return;
            }
            if (!order.globalDiscountPc) {
                return;
            }

            const percentage = order.globalDiscountPc;
            this.debouncedDiscount(percentage, order); // Wait an animation frame before applying the discount
        };

        this.models["pos.order.line"].addEventListener("update", (data) => {
            const line = this.models["pos.order.line"].get(data.id);
            const order = line.order_id;

            if (!line.isDiscountLine) {
                updateOrderDiscount(order);
            }
        });

        this.models["pos.order"].addEventListener("update", ({ id, fields }) => {
            const areAccountingFields = fields?.some((field) =>
                PosOrderAccounting.accountingFields.has(field)
            );

            if (areAccountingFields) {
                updateOrderDiscount(this.models["pos.order"].get(id));
            }
        });
    },
    selectOrderLine(order, line) {
        super.selectOrderLine(order, line);
        // Ensure the numpadMode should be `price` when the discount line is selected
        if (line?.isDiscountLine) {
            this.numpadMode = "price";
        }
    },
    async applyDiscount(percent, order = this.getOrder()) {
        const taxKey = (taxIds) =>
            taxIds
                .map((tax) => tax.id)
                .sort((a, b) => a - b)
                .join("_");

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

        const discountLinesMap = {};
        (order.discountLines || []).forEach((line) => {
            const key = taxKey(line.tax_ids);
            discountLinesMap[key] = line;
        });
        const isGlobalDiscountBtnClicked = Object.keys(discountLinesMap).length === 0;

        const lines = order.getOrderlines();
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
        let lastDiscountLine = null;
        for (const baseLine of globalDiscountBaseLines) {
            const extra_tax_data = accountTaxHelpers.export_base_line_extra_tax_data(baseLine);
            extra_tax_data.discount_percentage = percent;

            const key = taxKey(baseLine.tax_ids);
            const existingLine = discountLinesMap[key];

            if (existingLine) {
                existingLine.extra_tax_data = extra_tax_data;
                existingLine.price_unit = baseLine.price_unit;
                delete discountLinesMap[key];
            } else {
                lastDiscountLine = await this.addLineToOrder(
                    {
                        product_id: baseLine.product_id,
                        price_unit: baseLine.price_unit,
                        qty: baseLine.quantity,
                        tax_ids: [["link", ...baseLine.tax_ids]],
                        product_tmpl_id: baseLine.product_id.product_tmpl_id,
                        extra_tax_data: extra_tax_data,
                    },
                    order,
                    { force: true },
                    false
                );
            }
        }

        Object.values(discountLinesMap).forEach((line) => {
            line.delete();
        });

        if (lastDiscountLine && isGlobalDiscountBtnClicked) {
            order.selectOrderline(lastDiscountLine);
            this.numpadMode = "price";
        }
    },
});
