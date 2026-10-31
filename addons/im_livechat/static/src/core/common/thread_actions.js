import { registerThreadAction, threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

registerThreadAction("restart", {
    condition: ({ channel, owner }) =>
        channel?.chatbot?.canRestart && !owner.isDiscussSidebarChannelActions,
    icon: "refresh",
    name: _t("Restart Conversation"),
    onSelected: ({ channel, owner }) => {
        const chatWindow = owner.props?.chatWindow;
        chatWindow?.feedbackDoneResolver?.resolve(false);
        channel.chatbot.restart();
        chatWindow?.open({ focus: true });
    },
    sequence: 99,
    sequenceQuick: 15,
});

const callSettingsAction = threadActionsRegistry.get("call-settings");
patch(callSettingsAction, {
    condition({ channel, store }) {
        return channel?.selfMemberType === "visitor"
            ? store.rtc.localChannel?.eq(channel)
            : super.condition(...arguments);
    },
});
