import { registerThreadAction } from "@mail/core/common/thread_actions";
import { ActionCallButton } from "@mail/discuss/call/common/action_call_button";
import { ActionCallDropdown } from "@mail/discuss/call/common/action_call_dropdown";
import { CallSettings } from "@mail/discuss/call/common/call_settings";

import { _t } from "@web/core/l10n/translation";

registerThreadAction("call", {
    buttonComponent: ActionCallButton,
    dropdownComponent: ActionCallDropdown,
    condition: ({ channel, store }) => channel?.allowCalls && !channel?.eq(store.rtc.channel),
    icon: "phone",
    iconClass: "oi-filled",
    name: ({ channel }) => (channel?.hasRtcSessionActive ? _t("Join the Call") : _t("Start Call")),
    onSelected: ({ channel, store }) => store.rtc.requestToggleCall(channel),
    sequence: 10,
    sequenceQuick: 30,
    btnVariant: () => "btn-success",
});
registerThreadAction("camera-call", {
    buttonComponent: ActionCallButton,
    dropdownComponent: ActionCallDropdown,
    condition: ({ channel, store }) => channel?.allowCalls && !channel?.eq(store.rtc.channel),
    icon: "videocam",
    iconClass: "oi-filled",
    name: ({ channel }) =>
        channel?.hasRtcSessionActive ? _t("Join the Call with Camera") : _t("Start Video Call"),
    onSelected: ({ channel, store }) =>
        store.rtc.requestToggleCall(channel, {
            camera: true,
            fullscreen: !store.inPublicPage,
        }),
    sequence: 5,
    sequenceQuick: ({ owner }) => (owner.env.inDiscussApp ? 25 : 35),
    btnVariant: () => "btn-success",
});
registerThreadAction("call-settings", {
    actionPanelComponent: CallSettings,
    actionPanelComponentProps: () => ({ isCompact: true }),
    condition: ({ channel, owner, store }) =>
        channel?.allowCalls &&
        store.self_user &&
        (owner.props.chatWindow?.isOpen || store.inPublicPage) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "settings",
    iconClass: "oi-filled oi-fw",
    name: _t("Voice & Video Settings"),
    sequence: 5,
    sequenceGroup: 30,
});
registerThreadAction("disconnect", {
    buttonComponent: ActionCallButton,
    dropdownComponent: ActionCallDropdown,
    condition: ({ channel, owner, store }) =>
        store.rtc.selfSession?.in(channel?.rtc_session_ids) && owner.isDiscussSidebarChannelActions,
    onSelected: ({ channel, store }) => store.rtc.toggleCall(channel),
    icon: "phone",
    iconClass: "oi-filled",
    name: _t("Disconnect"),
    sequence: 30,
    sequenceGroup: 10,
    btnVariant: () => "btn-danger",
});
