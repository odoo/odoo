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
            thread.eq(component.message.thread) &&
            !component.message.hasNewMessageSeparator
        );
    },
    icon: "fa fa-eye-slash",
    /** @deprecated use `name` instead */
    title: (comp, action) => action.name,
    name: _t("Mark as Unread"),
    /** @deprecated use `onSelected` instead */
    onClick: (component, action, ...args) => action.onSelected(component, action, ...args),
    /** @param {import("@mail/core/common/message").Message} component */
    onSelected: (component) => {
        const message = toRaw(component.message);
        const selfMember = message.thread?.selfMember;
        if (selfMember) {
            selfMember.new_message_separator = message.id;
            selfMember.new_message_separator_ui = selfMember.new_message_separator;
        }
        message.thread.markedAsUnread = true;
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
    onSelected(component) {
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
        return super.onSelected(component);
    },
});
