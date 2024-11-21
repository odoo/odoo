/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

class ButtonWithNotification extends Component {
    static template = "purchase.ButtonWithNotification";
    static props = {
        ...standardWidgetProps,
        method: String,
        title: String,
    };
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
