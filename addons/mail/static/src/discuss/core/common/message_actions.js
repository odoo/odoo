import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";

import { toRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

messageActionsRegistry.add("set-new-message-separator", {
    /** @param {import("@mail/core/common/message").Message} component */
    condition: (component) => {
        const thread = component.props.thread;
        return (
            thread &&
            thread.selfMember &&
            component.isOriginThread &&
            !component.message.hasNewMessageSeparator
        );
    },
    icon: "fa fa-eye-slash",
    title: _t("Mark as Unread"),
    /** @param {import("@mail/core/common/message").Message} component */
    onClick: (component) => {
        const message = toRaw(component.message);
        rpc("/discuss/channel/set_new_message_separator", {
            channel_id: message.thread.id,
            message_id: message.id,
        });
    },
    sequence: 70,
});

const editAction = messageActionsRegistry.get("edit");

patch(editAction, {
    /** @param {import("@mail/core/common/message").Message} component */
    onClick(component) {
        const doc = createDocumentFragmentFromContent(component.message.body);
        const mentionedChannelElements = doc.querySelectorAll(".o_channel_redirect");
        component.message.mentionedChannelPromises = Array.from(mentionedChannelElements)
            .filter((el) => el.dataset.oeModel === "discuss.channel")
            .map(async (el) =>
                component.store.Thread.getOrFetch({
                    id: el.dataset.oeId,
                    model: el.dataset.oeModel,
                })
            );
        return super.onClick(component);
    },
});
