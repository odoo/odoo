/** @odoo-module */

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(OrderWidget, {
    props: {
        ...OrderWidget.props,
        isConfigRestaurant: { type: Boolean, optional: true },
        isOrderBooked: { type: Boolean, optional: true },
    },
});

patch(OrderWidget.prototype, {
    emptyCartText() {
        let text = super.emptyCartText(...arguments);
        if (this.props.isConfigRestaurant && !this.props.isOrderBooked) {
            text += " " + _t("or book the table for later");
        }
        return text;
    },
});
