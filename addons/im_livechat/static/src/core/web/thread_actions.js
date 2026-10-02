import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";
import { LivechatStatusSelection } from "@im_livechat/core/web/livechat_status_selection";
import { patch } from "@web/core/utils/patch";
import { joinChannelAction } from "@mail/discuss/core/public_web/thread_actions";

/** @type {import("@mail/core/common/action").PanelDefinition} */
const livechatInfoPanel = {
    class: "o-livechat-ChannelInfoList bg-inherit",
    component: LivechatChannelInfoList,
    props: ({ thread }) => ({ thread }),
};
registerThreadAction("livechat-info", {
    condition: ({ channel, owner, store }) =>
        channel?.channel_type === "livechat" &&
        store.self_user?.share === false &&
        !owner.isDiscussSidebarChannelActions,
    icon: "info",
    name: _t("Information"),
    panel: {
        ...livechatInfoPanel,
        onClose: ({ action, store }) => {
            if (action.condition) {
                store.discuss.isLivechatInfoPanelOpenByDefault = false;
            }
        },
        onOpen: ({ store }) => {
            store.discuss.isLivechatInfoPanelOpenByDefault = true;
        },
    },
    sequence: 10,
    sequenceGroup: 7,
});
registerThreadAction("livechat-status", {
    condition: ({ channel, store, owner }) =>
        channel?.channel_type === "livechat" &&
        store.has_access_livechat &&
        !channel.livechat_end_dt &&
        !owner.isDiscussContent,
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
    name: ({ channel }) => channel.livechatStatusLabel,
    nameClass: "fst-italic small",
    // the full information in a panel, only the status elsewhere, e.g. in a dropdown of the sidebar
    panel: ({ container }) =>
        container.type === "panel"
            ? livechatInfoPanel
            : {
                  class: "p-0",
                  component: LivechatStatusSelection,
                  props: ({ thread }) => ({ thread }),
              },
    sequence: ({ owner }) => (owner.isDiscussSidebarChannelActions ? 10 : 5),
    sequenceGroup: ({ owner }) => (owner.isDiscussSidebarChannelActions ? 5 : 7),
});

patch(joinChannelAction, {
    condition({ channel }) {
        return super.condition(...arguments) && !channel?.livechat_end_dt;
    },
    async onSelected({ channel, store }) {
        if (channel.livechat_status === "need_help") {
            const hasJoined = await store.env.services.orm.call(
                "discuss.channel",
                "livechat_join_channel_needing_help",
                [[channel.id]]
            );
            if (!hasJoined && channel?.isDisplayed) {
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
