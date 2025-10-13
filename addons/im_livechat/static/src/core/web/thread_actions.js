import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";
import { patch } from "@web/core/utils/patch";
import { joinChannelAction } from "@mail/discuss/core/web/thread_actions";

registerThreadAction("livechat-info", {
    actionPanelComponent: LivechatChannelInfoList,
    actionPanelOuterClass: "o-livechat-ChannelInfoList bg-inherit",
    condition: ({ channel, owner }) =>
        channel?.channel_type === "livechat" && !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-info",
    name: _t("Information"),
    sequence: 10,
    sequenceGroup: 7,
});
registerThreadAction("livechat-status", {
    actionPanelComponent: LivechatChannelInfoList,
    actionPanelOuterClass: "o-livechat-ChannelInfoList bg-inherit",
    condition: ({ channel, owner }) =>
        channel?.channel_type === "livechat" && !channel.livechat_end_dt && !owner.isDiscussContent,
    dropdown: true,
    dropdownMenuClass: "p-0",
    dropdownTemplate: "im_livechat.LivechatStatusSelection",
    dropdownTemplateParams: ({ thread }) => ({ livechatThread: thread }),
    icon: ({ channel, store }) => {
        const btn = store.livechatStatusButtons.find(
            (btn) => btn.status === channel.livechat_status
        );
        if (!btn) {
            return undefined;
        }
        return {
            template: "im_livechat.LivechatStatusLabel",
            params: { btn, inThreadActions: true },
        };
    },
    name: ({ thread }) => thread.livechatStatusLabel,
    nameClass: "fst-italic small",
    sequence: ({ owner }) => (owner.isDiscussSidebarChannelActions ? 10 : 5),
    sequenceGroup: ({ owner }) => (owner.isDiscussSidebarChannelActions ? 5 : 7),
});

patch(joinChannelAction, {
    async onSelected({ channel, store, thread }) {
        if (channel.livechat_status === "need_help") {
            const hasJoined = await store.env.services.orm.call(
                "discuss.channel",
                "livechat_join_channel_needing_help",
                [[channel.id]]
            );
            if (!hasJoined && thread.isDisplayed) {
                store.env.services.notification.add(
                    _t("Someone has already joined this conversation"),
                    { type: "warning" }
                );
            }
        } else {
            super.onSelected(...arguments);
        }
    },
});
