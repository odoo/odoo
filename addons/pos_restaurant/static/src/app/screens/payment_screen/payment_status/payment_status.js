import { patch } from "@web/core/utils/patch";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreenStatus.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },

    async onClickSplitAndPay() {
        const originOrder = this.order;
        if (!originOrder.isSplitPaymentAvailable) {
            return;
        }

        const shares = originOrder.splitPaymentShares;
        const floatingOrder = this.pos.addNewOrder({ floating_order_name: "Split Payment" });
        originOrder.transferSplitPaymentInfosTo(floatingOrder);

        for (const { baseLine, delta } of shares) {
            if (delta) {
                await this.addSplitPaymentLineToOrder(floatingOrder, baseLine, delta);
            }
        }

        originOrder.transferPaymentLinesTo(floatingOrder);

        for (const { baseLine, old } of shares) {
            if (old) {
                old.price_unit = baseLine.price_unit;
                old.setFullProductName();
            } else {
                await this.addSplitPaymentLineToOrder(originOrder, baseLine, baseLine.price_unit);
            }
        }

        await this._validateAndFinalizeOrders(originOrder, floatingOrder);
    },

    async _validateAndFinalizeOrders(originOrder, floatingOrder) {
        this.pos.setOrder(floatingOrder);
        const validated = await this.pos.validateOrder(floatingOrder);

        if (!validated) {
            this.pos.removeOrder(floatingOrder, false);
            this.pos.setOrder(originOrder);
            return;
        }

        this.pos.setOrder(originOrder);
    },

    async addSplitPaymentLineToOrder(order, baseLine, price_unit) {
        return this.pos.addLineToOrder(
            {
                product_id: order.splitPaymentProduct,
                product_tmpl_id: order.splitPaymentProduct.product_tmpl_id,
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
