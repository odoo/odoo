/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

class ButtonWithNotification extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClick() {
        const result = await this.orm.call(this.props.record.resModel, this.props.method, [
            this.props.record.resId,
        ]);
        const message = result.toast_message;
        this.notification.add(message, { type: "success" });
    }
}
ButtonWithNotification.template = "purchase.ButtonWithNotification";

export const buttonWithNotification = {
    component: ButtonWithNotification,
    extractProps: ({ attrs }) => {
        return {
            method: attrs.button_name,
            title: attrs.title,
        };
    },
};
registry.category("view_widgets").add("toaster_button", buttonWithNotification);
