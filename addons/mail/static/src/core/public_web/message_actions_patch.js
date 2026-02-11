import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("pin", {
    condition: ({ message, store, thread }) =>
        !message.pinned_at && store.self_user && message.thread && thread?.model !== "mail.box",
    icon: "fa fa-thumb-tack",
    name: _t("Pin"),
    onSelected: ({ message }) => (message.channel_id || message.thread).messagePin(message),
    sequence: 110,
});

registerMessageAction("unpin", {
    condition: ({ message, store, thread }) =>
        message.pinned_at && store.self_user && message.thread && thread?.model !== "mail.box",
    icon: "fa fa-thumb-tack",
    name: _t("Unpin"),
    onSelected: ({ message }) => (message.channel_id || message.thread).messageUnpin(message),
    sequence: 110,
});
