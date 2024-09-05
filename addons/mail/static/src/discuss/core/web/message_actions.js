import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

messageActionsRegistry.add("new-sub-channel", {
    condition: (component) =>
        component.isOriginThread && component.message.thread.hasSubThreadFeature,
    icon: "fa-rss",
    onClick: (component) => component.message.thread.createSubChannel(component.message),
    title: _t("Create Thread"),
    sequence: 75,
});
