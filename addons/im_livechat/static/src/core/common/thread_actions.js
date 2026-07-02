import { registerThreadAction, threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

registerThreadAction("restart", {
    condition: ({ channel, owner }) =>
        channel?.chatbot?.canRestart && !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-refresh",
    name: _t("Restart Conversation"),
    onSelected: ({ channel, owner }) => {
        owner.props.chatWindow.feedbackDoneResolver?.resolve(false);
        channel.chatbot.restart();
        owner.props.chatWindow.open({ focus: true });
    },
    sequence: 99,
    sequenceQuick: 15,
});

const callSettingsAction = threadActionsRegistry.get("call-settings");
patch(callSettingsAction, {
    condition({ channel, store }) {
        return channel?.channel_type === "livechat" &&
            this.channel?.self_member_id?.livechat_member_type === "visitor"
            ? store.rtc.localChannel?.eq(channel)
            : super.condition(...arguments);
    },
});
