/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

const { utils, Component } = owl;
const { escape } = utils;

export const displayNotificationAction = (env, action) => {
    const params = action.params || {};
    const options = {
        className: params.className || "",
        sticky: params.sticky || false,
        title: params.title,
        type: params.type || "info",
        messageIsHtml: true,
    };
    let links = (params.links || []).map((link) => {
        return `<a href="${escape(link.url)}" target="_blank">${escape(link.label)}</a>`;
    });
    const message = sprintf(escape(params.message), ...links);
    env.services.notification.add(message, options);
    return params.next;
};

registry.category("actions").add("display_notification", displayNotificationAction);

class InvalidAction extends Component {
    setup() {
        this.notification = useService("notification");
    }

    mounted() {
        const message = sprintf(
            this.env._t("No action with id '%s' could be found"),
            this.props.actionId
        );
        this.notification.add(message, { type: "danger" });
    }
}
InvalidAction.template = owl.tags.xml`<div class="o_invalid_action"></div>`;

registry.category("actions").add("invalid_action", InvalidAction);
