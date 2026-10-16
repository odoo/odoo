import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        const order = this.getSelectedOrder();
        const discountLines = order.discountLines;
        const destinationOrder = this.pos.getOrder();

        const globalDiscountPc = order.globalDiscountPc;
        if (discountLines?.length && destinationOrder && globalDiscountPc.type !== "fixed") {
            await this.pos.applyDiscount(
                globalDiscountPc.value,
                globalDiscountPc.type,
                destinationOrder
            );
        }
    },

    _onUpdateSelectedOrderline() {
        const order = this.getSelectedOrder();
        const orderline = order?.lines.find((line) => line.id === this.getSelectedOrderlineId());

        if (orderline && orderline.isDiscountLine) {
            return this.dialog.add(AlertDialog, {
                title: _t("Oh snap !"),
                body: _t("You cannot edit a discount line."),
            });
        }
        const result = super._onUpdateSelectedOrderline(...arguments);
        if (!order || order.globalDiscountPc.type !== "fixed") {
            return result;
        }

        const taxKey = (taxIds) =>
            taxIds
                .map((tax) => tax.id)
                .sort((a, b) => a - b)
                .join("_");

        const discountableLines = order.lines.filter((line) => line.isGlobalDiscountApplicable());
        const totalPriceMap = new Map();
        for (const line of discountableLines) {
            const key = taxKey(line.tax_ids);
            totalPriceMap.set(key, line.price_subtotal + (totalPriceMap.get(key) || 0));
        }

        const ratios = new Map();
        for (const orderline of discountableLines) {
            const key = taxKey(orderline.tax_ids);
            const total = totalPriceMap.get(key);
            if (!total || !orderline.qty) {
                continue;
            }
            const detail = this.getToRefundDetail(orderline);
            ratios.set(
                key,
                (ratios.get(key) || 0) +
                    (detail.qty / orderline.qty) * (orderline.price_subtotal / total)
            );
        }

        const productUnit = this.pos.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit"
        );
        for (const discountLine of order.discountLines) {
            const discountRefundDetail = this.getToRefundDetail(discountLine);
            if (!discountLine.price_unit) {
                continue;
            }
            const ratio = ratios.get(taxKey(discountLine.tax_ids)) || 0;
            discountRefundDetail.discountAmount = this.pos.currency.round(
                ratio * discountLine.price_unit
            );
            discountRefundDetail.qty = Math.min(
                productUnit.round(ratio),
                discountRefundDetail.refundableQty
            );
        }

        return result;
    },

    getRefundLinesDetails(refundDetail) {
        const vals = super.getRefundLinesDetails(...arguments);
        if (refundDetail.line.isDiscountLine && refundDetail.qty && refundDetail.discountAmount) {
            vals.price_unit = refundDetail.discountAmount / refundDetail.qty;
        }
        return vals;
    },

    onClickOrderline(orderline) {
        if (
            this.getSelectedOrder()?.finalized &&
            this.getSelectedOrderlineId() == orderline.id &&
            orderline.isDiscountLine
        ) {
            return this.dialog.add(AlertDialog, {
                title: _t("Oh snap !"),
                body: _t("You cannot edit a discount line."),
            });
        }
        return super.onClickOrderline(...arguments);
    },
});
