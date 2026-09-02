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
            this.pos.applyDiscount(globalDiscountPc.value, globalDiscountPc.type, destinationOrder);
        }
    },

    _onUpdateSelectedOrderline() {
        const order = this.getSelectedOrder();
        const lines = order.lines;
        const selectedOrderline = lines.find((line) => line.id === this.getSelectedOrderlineId());

        if (selectedOrderline && selectedOrderline.isDiscountLine) {
            return this.dialog.add(AlertDialog, {
                title: _t("Oh snap !"),
                body: _t("You cannot edit a discount line."),
            });
        }
        const result = super._onUpdateSelectedOrderline(...arguments);
        if (order.globalDiscountPc.type !== "fixed") {
            return result;
        }

        const taxKey = (taxIds) =>
            taxIds
                .map((tax) => tax.id)
                .sort((a, b) => a - b)
                .join("_");

        const refundableLines = lines.filter((line) => !line.isDiscountLine);
        const totalPriceMap = new Map();
        for (const line of refundableLines) {
            const key = taxKey(line.tax_ids);
            totalPriceMap.set(key, line.price_subtotal_incl + (totalPriceMap.get(key) || 0));
        }

        const ratios = new Map();
        for (const orderline of refundableLines) {
            const key = taxKey(orderline.tax_ids);
            const total = totalPriceMap.get(key);
            if (!total) {
                continue;
            }
            const detail = this.getToRefundDetail(orderline);
            ratios.set(
                key,
                (ratios.get(key) || 0) +
                    (detail.qty / orderline.qty) *
                        (orderline.price_subtotal_incl / totalPriceMap.get(key))
            );
        }

        for (const discountLine of order.discountLines) {
            const discountRefundDetail = this.getToRefundDetail(discountLine);
            if (!discountLine.price_unit) {
                continue;
            }
            const qty =
                this.pos.currency.round(
                    (ratios.get(taxKey(discountLine.tax_ids)) || 0) * discountLine.price_unit
                ) / discountLine.price_unit;
            if (qty !== discountRefundDetail.qty) {
                this._setToRefundDetail(discountRefundDetail, qty.toString());
            }
        }

        return result;
    },

    onClickOrderline(orderline) {
        if (
            this.getSelectedOrder()?.finalized &&
            this.getSelectedOrderlineId() == orderline.id &&
            orderline.product_id.id === this.pos.config.discount_product_id?.id
        ) {
            {
                return this.dialog.add(AlertDialog, {
                    title: _t("Oh snap !"),
                    body: _t("You cannot edit a discount line."),
                });
            }
        }
        return super.onClickOrderline(...arguments);
    },
});
