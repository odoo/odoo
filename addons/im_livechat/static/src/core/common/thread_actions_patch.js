import { threadActionsInternal, threadActionsRegistry } from "@mail/core/common/thread_actions";
import { patch } from "@web/core/utils/patch";
import "@mail/discuss/core/common/thread_actions"; // for "invite-people" definition
import { LivechatChannelInfoList } from "./livechat_channel_info_list";
import { _t } from "@web/core/l10n/translation";

patch(threadActionsInternal, {
    precondition(component, id, action) {
        const allowedThreadActions = new Set([
            "fold-chat-window",
            "close",
            "restart",
            "call-settings",
        ]);
        if (
            !component.thread ||
            (component.thread?.channel_type === "livechat" &&
                !["agent", "bot"].includes(component.thread?.selfMember?.livechat_member_type) &&
                !allowedThreadActions.has(id) &&
                !(component.store.self?.main_user_id?.share === false))
        ) {
            return false;
        }
        return super.precondition(component, id, action);
    },
});

patch(threadActionsRegistry.get("invite-people"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && !component.thread.livechat_end_dt;
        }
        return super.condition(component);
    },
});

patch(threadActionsRegistry.get("notification-settings"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && !component.thread.livechat_end_dt;
        }
        return super.condition(component);
    },
});

patch(threadActionsRegistry.get("camera-call"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && !component.thread.livechat_end_dt;
        }
        return super.condition(component);
    },
});

patch(threadActionsRegistry.get("call"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && !component.thread.livechat_end_dt;
        }
        return super.condition(component);
    },
});

threadActionsRegistry.add("livechat-info", {
    component: LivechatChannelInfoList,
    condition(component) {
        return component.thread?.channel_type === "livechat";
    },
    panelOuterClass: "o-livechat-ChannelInfoList bg-inherit",
    icon: "fa fa-fw fa-info",
    iconLarge: "fa fa-fw fa-lg fa-info",
    name: _t("Information"),
    nameActive: _t("Close Information"),
    sequence: 10,
    sequenceGroup: 7,
    toggle: true,
});
