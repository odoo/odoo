import { patch } from "@web/core/utils/patch";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

const taxKey = (taxes) =>
    taxes
        .map((t) => t.id)
        .sort((a, b) => a - b)
        .join(",");

patch(PaymentScreenStatus.prototype, {
    async onClickSplitAndPay() {
        const originOrder = this.order;
        const splitProduct = this.pos.config.split_payment_product_id;
        if (!splitProduct) {
            this.dialog.add(AlertDialog, {
                title: _t("No split payment product found"),
                body: _t(
                    "The split payment product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."
                ),
            });
            return;
        }

        const paymentLines = [...originOrder.payment_ids];
        const paidAmount = paymentLines.reduce((sum, l) => sum + l.amount, 0);
        if (paidAmount <= 0) {
            return;
        }

        const existingSplitLines = new Map();
        let alreadySplit = 0;
        for (const line of originOrder.splitPaymentLines || []) {
            existingSplitLines.set(taxKey(line.tax_ids), line);
            alreadySplit -= line.priceIncl;
        }

        if (paidAmount >= originOrder.priceIncl) {
            return;
        }

        const newBaseLines = this.computeSplitBaseLines(originOrder, alreadySplit + paidAmount);
        const parts = newBaseLines.map((baseLine) => {
            const key = taxKey(baseLine.tax_ids);
            const old = existingSplitLines.get(key);
            return {
                key,
                baseLine,
                old,
                delta: (old ? old.price_unit : 0) - baseLine.price_unit,
            };
        });

        const floatingOrder = this.pos.addNewOrder({ floating_order_name: "Split Payment" });
        floatingOrder.split_payment_origin_uuid = originOrder.uuid;
        for (const { baseLine, delta } of parts) {
            if (delta) {
                await this.addSplitPaymentLine(floatingOrder, baseLine, delta);
            }
        }

        for (const line of paymentLines) {
            const result = floatingOrder.addPaymentline(line.payment_method_id);
            if (result.status && result.data) {
                result.data.setAmount(line.amount);
            }
        }
        for (const line of paymentLines) {
            originOrder.removePaymentline(line);
        }

        for (const { baseLine, old } of parts) {
            if (old) {
                old.price_unit = baseLine.price_unit;
                old.setFullProductName();
            } else {
                await this.addSplitPaymentLine(originOrder, baseLine, baseLine.price_unit);
            }
        }

        this.pos.setOrder(floatingOrder);
        const validated = await this.pos.validateOrder(floatingOrder);
        if (!validated) {
            this.pos.removeOrder(floatingOrder, false);
            this.pos.setOrder(originOrder);
            return;
        }

        this.pos.setOrder(originOrder);
    },

    computeSplitBaseLines(order, amount) {
        const splitProduct = this.pos.config.split_payment_product_id;
        const lines = order.getOrderlines().filter((l) => !l.isSplitPaymentLine);
        const baseLines = lines.map((line) => line.getBaseLine());
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, order.company_id);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, order.company_id);

        return accountTaxHelpers.prepare_global_discount_lines(
            baseLines,
            order.company_id,
            "fixed",
            order.isRefund ? -amount : amount,
            {
                computation_key: "split_payment",
                grouping_function: () => ({
                    grouping_key: { product_id: splitProduct },
                    raw_grouping_key: { product_id: splitProduct.id },
                }),
            }
        );
    },

    async addSplitPaymentLine(order, baseLine, price_unit) {
        const splitProduct = this.pos.config.split_payment_product_id;
        return this.pos.addLineToOrder(
            {
                product_id: splitProduct,
                product_tmpl_id: splitProduct.product_tmpl_id,
                qty: baseLine.quantity,
                price_unit,
                tax_ids: [["link", ...baseLine.tax_ids]],
            },
            order,
            { force: true },
            false
        );
    },
});
