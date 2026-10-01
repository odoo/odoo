import { registerThreadAction, threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";
import "@mail/discuss/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { redirect } from "@web/core/utils/urls";

patch(threadActionsRegistry.get("expand-discuss"), {
    condition: ({ channel, owner, store }) =>
        store.self_user?.share === true &&
        channel?.channel_type === "livechat" &&
        !channel.isTransient &&
        channel.self_member_id &&
        owner.props.chatWindow?.isOpen &&
        !store.env.services.ui.isSmall,
    onSelected({ channel }) {
        redirect(`/discuss/channel/${channel.id}`);
    },
});

registerThreadAction("restart", {
    condition: ({ channel, owner }) =>
        channel?.chatbot?.canRestart && !owner.isDiscussSidebarChannelActions,
    icon: "refresh",
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
        return channel?.channel_type === "livechat"
            ? store.rtc.localChannel?.eq(channel)
            : super.condition(...arguments);
    },
});
