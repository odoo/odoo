import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

messageActionsRegistry.add("create-or-view-thread", {
    condition: (component) =>
        component.message.thread?.eq(component.props.thread) &&
        component.message.thread.hasSubChannelFeature &&
        component.store.self_partner?.main_user_id?.share === false,
    icon: "fa fa-comments-o",
    onClick: (component) => {
        if (component.message.linkedSubChannel) {
            component.message.linkedSubChannel.open({ focus: true });
        } else {
            component.message.thread.createSubChannel({ initialMessage: component.message });
        }
    },
    title: (component) =>
        component.message.linkedSubChannel ? _t("View Thread") : _t("Create Thread"),
    sequence: 75,
});
