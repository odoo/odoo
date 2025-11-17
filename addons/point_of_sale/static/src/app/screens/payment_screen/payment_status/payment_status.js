import { Component } from "@odoo/owl";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class PaymentScreenStatus extends Component {
    static template = "point_of_sale.PaymentScreenStatus";
    static props = {
        order: Object,
    };
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
        return this.env.utils.formatCurrency(this.currentTip.amount);
    }

    get changeText() {
        return this.env.utils.formatCurrency(this.props.order.getChange());
    }

    get isComplete() {
        return this.isRemaining && this.order.orderHasZeroRemaining;
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
