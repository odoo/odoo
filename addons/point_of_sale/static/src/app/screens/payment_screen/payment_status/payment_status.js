import { Component } from "@odoo/owl";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { _t } from "@web/core/l10n/translation";

export class PaymentScreenStatus extends Component {
    static template = "point_of_sale.PaymentScreenStatus";
    static props = {
        order: Object,
    };
    static components = { PriceFormatter };

    get isComplete() {
        return this.isRemaining && this.order.orderHasZeroRemaining;
    }

    get isIncompleteAndPositive() {
        return !this.isComplete && this.order.remainingDue > 0;
    }

    get order() {
        return this.props.order;
    }

    get isRemaining() {
        const isNegative = this.order.totalDue < 0;
        const remainingDue = this.order.remainingDue;

        if ((isNegative && remainingDue > 0) || (!isNegative && remainingDue <= 0)) {
            return false;
        } else {
            return true;
        }
    }

    get statusText() {
        if (!this.isRemaining) {
            return _t("Change");
        } else {
            return _t("Remaining");
        }
    }

    get amountText() {
        if (!this.isRemaining) {
            return this.env.utils.formatCurrency(this.order.change);
        } else {
            return this.env.utils.formatCurrency(this.order.remainingDue);
        }
    }
}
