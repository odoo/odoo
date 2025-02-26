import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

messageActionsRegistry.add("copy-link", {
    condition: (component) =>
        component.message.message_type && component.message.message_type !== "user_notification",
    icon: "fa fa-link",
    title: _t("Copy Link"),
    onClick: (component) => component.message.copyLink(),
    sequence: 110,
});
