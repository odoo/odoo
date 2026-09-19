import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("pin", {
    condition: ({ message, owner }) =>
        !owner.env.inMessagingMenu && !message.pinned_at && message.canTogglePin,
    icon: "push_pin",
    name: _t("Pin"),
    onSelected: ({ action, message }) =>
        (message.channel_id || message.thread).messagePin(message, { rootRef: action.actionRef }),
    sequence: 70,
});

registerMessageAction("unpin", {
    condition: ({ message, owner }) =>
        !owner.env.inMessagingMenu && message.pinned_at && message.canTogglePin,
    icon: "push_pin",
    name: _t("Unpin"),
    onSelected: ({ action, message }) =>
        (message.channel_id || message.thread).messageUnpin(message, { rootRef: action.actionRef }),
    sequence: 70,
});
