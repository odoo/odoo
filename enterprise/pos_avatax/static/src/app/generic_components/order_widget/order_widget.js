import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";

patch(OrderWidget, {
    props: {
        ...OrderWidget.props,
        refreshAvatax: { type: Function, optional: true },
    },
});

patch(OrderWidget.prototype, {
    async refreshAvatax() {
        if (!this.props.refreshAvatax) {
            return;
        }

        await this.props.refreshAvatax();
    },
});
