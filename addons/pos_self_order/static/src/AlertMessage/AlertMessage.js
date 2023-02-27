/** @odoo-module */

const { Component } = owl;
import { _t } from "@web/core/l10n/translation";
const alert_index = {
    success: {
        class: "alert alert-success",
        message: "Order has been successfully placed.",
    },
    pay_success: {
        class: "alert alert-success",
        message: "Payment has been successfully processed.",
    },
    error: {
        class: "alert alert-danger",
        message: "Order was not successful. Please contact the restaurant.",
    },
    pay_error: {
        class: "alert alert-danger",
        message: "Payment was not successful. Please contact the restaurant.",
    },
    restaurant_is_closed: {
        class: "alert alert-danger",
        title: "The restaurant is closed",
        message: "You can still view the menu, but you will not be able to order.",
    },
    order_needs_payment: {
        class: "alert alert-primary",
        message: "Your order will be sent to the kitchen after payment.",
    },
};
export class AlertMessage extends Component {
    setup() {
        const alert_type = this.props.alert_type;
        this.alert =
            alert_type in alert_index
                ? alert_index[alert_type]
                : { class: "alert alert-primary", message: alert_type };
    }
}
AlertMessage.template = "AlertMessage";
export default { AlertMessage };
