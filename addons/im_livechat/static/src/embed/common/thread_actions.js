import { registerThreadAction, threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

registerThreadAction("restart", {
    condition(component) {
        return component.thread?.chatbot?.canRestart;
    },
    icon: "fa fa-fw fa-refresh",
    iconLarge: "fa fa-lg fa-fw fa-refresh",
    name: _t("Restart Conversation"),
    open(component) {
        component.thread.chatbot.restart();
        component.props.chatWindow.open({ focus: true });
    },
    sequence: 99,
    sequenceQuick: 15,
});

const callSettingsAction = threadActionsRegistry.get("call-settings");
patch(callSettingsAction, {
    condition(component) {
        return component.thread?.channel_type === "livechat"
            ? component.env.services["discuss.rtc"].state.channel?.eq(component.thread)
            : super.condition(...arguments);
    },
});
