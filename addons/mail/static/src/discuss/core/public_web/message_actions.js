import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

import { createDocumentFragmentFromContent } from "@mail/utils/common/html";
messageActionsRegistry.add("create-or-view-thread", {
    condition: (component) =>
        component.message.thread?.eq(component.props.thread) &&
        component.message.thread.hasSubChannelFeature &&
        component.store.self.isInternalUser,
    icon: "fa fa-comments-o",
    onClick: (component) => {
        const textContent = createDocumentFragmentFromContent(component.message.body).body
            .textContent;
        if (component.message.linkedSubChannel) {
            component.message.linkedSubChannel.open({ focus: true });
        } else {
            component.message.thread.createSubChannel({
                initialMessage: component.message,
                name: textContent,
            });
        }
    },
    title: (component) =>
        component.message.linkedSubChannel ? _t("View Thread") : _t("Create Thread"),
    sequence: 75,
});
