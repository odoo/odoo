import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(OrderWidget, {
    props: {
        ...OrderWidget.props,
        orderAcceptTime: { type: Number, optional: true },
        orderPrepTime: { type: Number, optional: true },
    },
});

patch(OrderWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this.state = useState({ remainingTime: 0 });
        this.state.remainingTime = this._computeRemainingTime();
        this.interval = setInterval(() => {
            this.state.remainingTime = this._computeRemainingTime();
        }, 10000);
    },

    _computeRemainingTime() {
        if (this.showTimer) {
            const total_order_time =
                this.props.orderAcceptTime + this.props.orderPrepTime * 60 * 1000;
            return Math.round((total_order_time - luxon.DateTime.now().ts) / (1000 * 60));
        }
    },

    get showTimer() {
        return this.props.orderAcceptTime && this.props.lines[0]?.order_id?.state !== "paid";
    },
});
