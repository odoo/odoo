import { Component } from "@odoo/owl";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { _t } from "@web/core/l10n/translation";

export class PaymentScreenStatus extends Component {
    static template = "point_of_sale.PaymentScreenStatus";
    static props = {
        order: Object,
    };
    static components = { PriceFormatter };

<<<<<<< b575bdc8cb71bf33a94ae2090e847bc37488364a
    get isComplete() {
        return this.isRemaining && this.order.orderHasZeroRemaining;
||||||| 3eb3393c7a19de483ba3afefeb207401fe45218c
    get changeText() {
        return this.env.utils.formatCurrency(this.props.order.getChange());
=======
    get changeText() {
        return this.env.utils.formatCurrency(-this.props.order.getChange());
>>>>>>> 53b9245a20deac9e17eec78356371aaca0ec8add
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
