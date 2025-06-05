import { Component, useState, useEffect } from "@odoo/owl";
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

        this.state = useState({ tip: this.pos.getTip() });
        useEffect(
            () => {
                this.state.tip = this.pos.getTip();
            },
            () => [this.pos.getTip()]
        );
    }

    get tipLabel() {
        let label = "Tip";
        if (this.state.tip.type === "percent") {
            label = _t(`Tip (%s%%)`, this.state.tip.value);
        }
        return label;
    }

    get tipText() {
        return this.env.utils.formatCurrency(this.state.tip.amount);
    }

    get changeText() {
        return this.env.utils.formatCurrency(this.props.order.getChange());
    }
    get remainingText() {
        const { order_remaining, order_sign } = this.props.order.taxTotals;
        if (this.props.order.orderHasZeroRemaining) {
            return this.env.utils.formatCurrency(0);
        }
        return this.env.utils.formatCurrency(order_sign * order_remaining);
    }
}
