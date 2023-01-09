/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape, sprintf } from "@web/core/utils/strings";

import { Component, onMounted, xml } from "@odoo/owl";

export function displayNotificationAction(env, action) {
    const params = action.params || {};
    const options = {
        className: params.className || "",
        sticky: params.sticky || false,
        title: params.title,
        type: params.type || "info",
    };
    const links = (params.links || []).map((link) => {
        return `<a href="${escape(link.url)}" target="_blank">${escape(link.label)}</a>`;
    });
    const message = owl.markup(sprintf(escape(params.message), ...links));
    env.services.notification.add(message, options);
    return params.next;
}

registry.category("actions").add("display_notification", displayNotificationAction);

class InvalidAction extends Component {
    setup() {
        this.notification = useService("notification");
        onMounted(this.onMounted);
    }

    onMounted() {
        const message = sprintf(
            this.env._t("No action with id '%s' could be found"),
            this.props.actionId
        );
        this.notification.add(message, { type: "danger" });
    }
}
InvalidAction.template = xml`<div class="o_invalid_action"></div>`;

registry.category("actions").add("invalid_action", InvalidAction);
