/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape, sprintf } from "@web/core/utils/strings";

const { Component, onMounted, xml } = owl;

export function displayNotificationAction(env, action) {
    const params = action.params || {};
    const options = {
        className: params.className || "",
        sticky: params.sticky || false,
        title: params.title,
        type: params.type || "info",
    };
    let links = (params.links || []).map((link) => {
        let target = '_blank';
        if ('target' in link) {
            if (link.target == 'current') {
                target = '_self';
            }
        }
        return `<a href="${escape(link.url)}" target="${target}">${escape(link.label)}</a>`;
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
