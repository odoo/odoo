import { Component, useProps, t } from "@odoo/owl";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";
import OrderPaymentValidation from "../../../utils/order_payment_validation";

export class PaymentScreenStatus extends Component {
    static template = "point_of_sale.PaymentScreenStatus";
    props = useProps({
        order: t.instanceOf(PosOrder),
    });
    static components = { PriceFormatter };

    setup() {
        this.pos = usePos();
    }

    get currentTip() {
        return this.pos.getTip();
    }

    get tipLabel() {
        let label = "Tip";
        if (this.currentTip.type === "percent") {
            label = _t(`Tip (%s%)`, this.currentTip.value);
        }
        return label;
    }

    get tipText() {
        return this.pos.formatCurrency(this.currentTip.amount);
    }

    get changeText() {
        return this.pos.formatCurrency(this.props.order.getChange());
    }

    get isComplete() {
        return this.order.hasRemainingDue && this.order.orderHasZeroRemaining;
    }

    get isIncompleteAndPositive() {
        return !this.isComplete && this.order.remainingDue > 0;
    }

    get order() {
        return this.props.order;
    }

    get showStatus() {
        return Boolean(this.order.remainingDue || this.order.change);
    }

    get amountText() {
        return this.pos.formatCurrency(this.order.remainingDueAmount, this.order.orderCurrency.id);
    }

    async onClickSplitAndPay() {
        const originOrder = this.props.order;
        const paymentLines = originOrder.payment_ids;
        const paidAmount = paymentLines.reduce((sum, line) => sum + line.amount, 0);

        if (paidAmount <= 0) {
            return;
        }

        const splitProduct = this.pos.config.split_payment_product_id;

        const floatingOrder = this.pos.addNewOrder({ floating_order_name: "Split Payment" });
        floatingOrder.split_payment_origin_uuid = originOrder.uuid;

        await this.pos.addLineToOrder(
            {
                product_id: splitProduct,
                product_tmpl_id: splitProduct.product_tmpl_id,
                qty: 1,
                price_unit: paidAmount,
            },
            floatingOrder
        );

        await this.pos.addLineToOrder(
            {
                product_id: splitProduct,
                product_tmpl_id: splitProduct.product_tmpl_id,
                qty: 1,
                price_unit: -paidAmount,
            },
            originOrder
        );

        for (const line of [...paymentLines]) {
            const method = line.payment_method_id;
            const amount = line.amount;

            const result = floatingOrder.addPaymentline(method);

            if (result.status && result.data) {
                result.data.setAmount(amount);
            }

            originOrder.removePaymentline(line);
        }

        this.pos.setOrder(floatingOrder);

        const validationOptions = this.pos.getValidationOrderOptions({ order: floatingOrder });
        const validation = new OrderPaymentValidation(validationOptions);

        return await validation.validateOrder(false);
    }
}
