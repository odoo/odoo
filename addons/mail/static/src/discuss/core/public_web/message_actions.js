import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

messageActionsRegistry.add("create-thread", {
    condition: (component) =>
        component.isOriginThread && component.message.thread.hasSubThreadFeature,
    icon: "fa-comments-o",
    onClick: (component) =>
        component.message.thread.createSubChannel({ initialMessage: component.message }),
    title: _t("Create Thread"),
    sequence: 75,
});
