import { registerThreadAction, threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

registerThreadAction("restart", {
    condition: ({ ancestors, channel }) =>
        channel?.chatbot?.canRestart && !ancestors.inMessagingMenu,
    icon: "refresh",
    name: _t("Restart Conversation"),
    onSelected: ({ channel, chatWindow }) => {
        chatWindow.feedbackDoneResolver?.resolve(false);
        channel.chatbot.restart();
        chatWindow.open({ focus: true });
    },
    sequence: 99,
    sequenceQuick: 15,
});

const callSettingsAction = threadActionsRegistry.get("call-settings");
patch(callSettingsAction, {
    condition({ channel, store }) {
        return channel?.channel_type === "livechat"
            ? store.rtc.localChannel?.eq(channel)
            : super.condition(...arguments);
    },
});
