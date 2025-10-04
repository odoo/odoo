/* @odoo-module */

import { messageActionsRegistry } from "@mail/core/common/message_actions";

messageActionsRegistry.add("pin", {
    condition: (component) =>
        component.store.user && component.props.thread.model === "discuss.channel",
    icon: "fa-thumb-tack",
    title: (component) => component.getPinOptionText(),
    onClick: (component) => component.onClickPin(),
    sequence: 65,
});
