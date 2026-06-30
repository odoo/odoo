import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("pin", {
    condition: ({ message, store, thread }) =>
        !message.pinned_at &&
        store.self_user &&
        message.thread &&
        (!message.channel_id || message.channel_id.canSelfInteractWithChannel),
    icon: "fa fa-thumb-tack",
    name: _t("Pin"),
    onSelected: ({ action, message }) =>
        (message.channel_id || message.thread).messagePin(message, { rootRef: action.actionRef }),
    sequence: 70,
});

registerMessageAction("unpin", {
    condition: ({ message, store, thread }) =>
        message.pinned_at &&
        store.self_user &&
        message.thread &&
        (!message.channel_id || message.channel_id.canSelfInteractWithChannel),
    icon: "fa fa-thumb-tack",
    name: _t("Unpin"),
    onSelected: ({ action, message }) =>
        (message.channel_id || message.thread).messageUnpin(message, { rootRef: action.actionRef }),
    sequence: 70,
});
