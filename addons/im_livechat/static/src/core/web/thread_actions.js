import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";

registerThreadAction("livechat-info", {
    actionPanelComponent: LivechatChannelInfoList,
    condition(component) {
        return (
            component.thread?.channel_type === "livechat" &&
            !component.isDiscussSidebarChannelActions
        );
    },
    panelOuterClass: "o-livechat-ChannelInfoList bg-inherit",
    icon: "fa fa-fw fa-info",
    iconLarge: "fa fa-fw fa-lg fa-info",
    name: _t("Information"),
    sequence: 10,
    sequenceGroup: 7,
    toggle: true,
});
registerThreadAction("livechat-status", {
    actionPanelComponent: LivechatChannelInfoList,
    condition(component) {
        return (
            component.thread?.channel_type === "livechat" &&
            !component.thread.livechat_end_dt &&
            !component.isDiscussContent
        );
    },
    dropdown: {
        template: "im_livechat.LivechatStatusAction",
        menuClass: "p-0 m-0 o-rounded-bubble",
    },
    panelOuterClass: "o-livechat-ChannelInfoList bg-inherit",
    icon: (component) => {
        const btn = component.store.livechatStatusButtons.find(
            (btn) => btn.status === component.thread.livechat_status
        );
        if (!btn) {
            return undefined;
        }
        return {
            template: "im_livechat.LivechatStatusLabel",
            params: { btn, inThreadActions: true },
        };
    },
    iconLarge: (component) => {
        const btn = component.store.livechatStatusButtons.find(
            (btn) => btn.status === component.thread.livechat_status
        );
        if (!btn) {
            return undefined;
        }
        return {
            template: "im_livechat.LivechatStatusLabel",
            params: { btn, inThreadActions: true },
        };
    },
    name: (component) => component.thread.livechatStatusLabel,
    nameClass: "fst-italic small mx-2",
    sequence: (component) => (component.isDiscussSidebarChannelActions ? 10 : 5),
    sequenceGroup: (component) => (component.isDiscussSidebarChannelActions ? 5 : 7),
    toggle: true,
});
registerThreadAction("join-livechat-needing-help", {
    condition: (comp) =>
        comp.thread?.livechat_status === "need_help" &&
        !comp.thread?.selfMember &&
        !comp.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-sign-in",
    iconLarge: "fa fa-fw fa-lg fa-sign-in",
    name: _t("Join Chat"),
    nameClass: "text-success",
    async open(component) {
        const thread = component.thread;
        const hasJoined = await component.env.services.orm.call(
            "discuss.channel",
            "livechat_join_channel_needing_help",
            [[thread.id]]
        );
        if (!hasJoined && thread.isDisplayed) {
            component.env.services.notification.add(
                _t("Someone has already joined this conversation"),
                { type: "warning" }
            );
        }
    },
    sequence: 5,
});
