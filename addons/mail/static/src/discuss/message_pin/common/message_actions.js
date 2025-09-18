import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";
registerMessageAction("pin", {
    condition: ({ store, thread }) =>
        store.self_partner && thread?.model === "discuss.channel",
    icon: "fa fa-thumb-tack",
    name: ({ message }) => (message.pinned_at ? _t("Unpin") : _t("Pin")),
    onSelected: ({ message }) => message.pin(),
    sequence: 65,
});
