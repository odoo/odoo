/* @odoo-module */

import { messageActionsRegistry } from "@mail/core/common/message_actions";

messageActionsRegistry.add("pin", {
    condition: (component) => component.store.self.partnerId && component.props.thread.channelId,
    icon: "fa-thumb-tack",
    title: (component) => component.getPinOptionText(),
    onClick: (component) => component.onClickPin(),
    sequence: 65,
});
