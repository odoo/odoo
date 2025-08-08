import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("create-or-view-thread", {
    condition: (component) =>
        component.message.thread?.eq(component.props.thread) &&
        component.message.thread.hasSubChannelFeature &&
        component.store.self.main_user_id?.share === false,
    icon: "fa fa-comments-o",
    iconLarge: "fa fa-lg fa-comments-o",
    onSelected: (component) => {
        if (component.message.linkedSubChannel) {
            component.message.linkedSubChannel.open({ focus: true });
        } else {
            component.message.thread.createSubChannel({ initialMessage: component.message });
        }
    },
    name: (component) =>
        component.message.linkedSubChannel ? _t("View Thread") : _t("Create Thread"),
    sequence: 75,
});
