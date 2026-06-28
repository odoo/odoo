import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ChangeLayoutDialog } from "@mail/discuss/call/common/change_layout_dialog";
import { QuickVoiceSettings } from "@mail/discuss/call/common/quick_voice_settings";
import { QuickVideoSettings } from "@mail/discuss/call/common/quick_video_settings";
import { attClassObjectToString } from "@mail/utils/common/format";
import { CALL_PROMOTE_FULLSCREEN } from "@mail/discuss/call/common/discuss_channel_model_patch";
import { MicrophoneWarning } from "@mail/discuss/call/common/microphone_warning";
import { Component, useEffect } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";

export const callActionsRegistry = registry.category("discuss.call/actions");
export const CALL_ICON_DEAFEN = "fa fa-deaf";
export const CALL_ICON_MUTED = "fa fa-microphone-slash";

/** @typedef {import("models").DiscussChannel} DiscussChannel */
/**
 * @typedef {Object} CallActionSpecificParams
 * @property {DiscussChannel} channel
 */
/** @typedef {import("@mail/core/common/action").ActionParams<CallAction, UseCallActions_Def> & CallActionSpecificParams} CallActionParams */
/** @typedef {import("@mail/core/common/action").ActionDefinition<CallActionParams, CallAction>} CallActionDefinition */

/**
 * @param {string} id
 * @param {CallActionDefinition} definition
 */
export function registerCallAction(id, definition) {
    callActionsRegistry.add(id, definition);
}

/** @type {CallActionDefinition} */
export const muteAction = {
    badge: ({ store }) =>
        store.rtc.microphonePermission !== "granted" || store.rtc.showMicrophoneSilentWarning,
    badgeIcon: "fa fa-exclamation",
    condition: ({ owner, store, channel }) =>
        channel?.isSelfInCall && (owner.env.inCallMenu || !store.rtc.selfSession?.is_deaf),
    disabledCondition: ({ store }) => store.rtc.showMicrophoneSilentWarning,
    name: ({ store }) => (store.rtc.selfSession?.isMute ? _t("Unmute") : _t("Mute")),
    isActive: ({ store }) => store.rtc.selfSession?.isMute,
    icon: ({ action, owner, store }) =>
        action.isActive
            ? store.rtc.selfSession?.is_deaf && !owner.env.inCallMenu
                ? CALL_ICON_DEAFEN
                : CALL_ICON_MUTED
            : "fa fa-microphone",
    hotkey: "shift+m",
    onSelected: ({ action, store }) => store.rtc.toggleMicrophone({ rootRef: action.actionRef }),
    sequence: 10,
    sequenceGroup: 100,
    setup({ action, owner, store }) {
        if (owner instanceof Component) {
            this.popover = usePopover(MicrophoneWarning, {
                closeOnClickAway: false,
                closeOnEscape: false,
                position: "top-middle",
            });
            useEffect(() => {
                const hasWarning =
                    store.rtc.showMicrophonePermissionWarning ||
                    store.rtc.showMicrophoneSilentWarning;
                if (!action.popover.isOpen && action.actionRef() && hasWarning) {
                    action.popover.open(action.actionRef(), {});
                } else {
                    action.popover.close();
                }
            });
        }
    },
    tags: ({ action, store }) => {
        const tags = [ACTION_TAGS.CALL_ACTION_TRACKED];
        if (action.isActive) {
            tags.push(ACTION_TAGS.DANGER);
        }
        if (store.rtc.microphonePermission !== "granted" || store.rtc.showMicrophoneSilentWarning) {
            tags.push(ACTION_TAGS.DANGER, ACTION_TAGS.WARNING_BADGE);
        }
        return tags;
    },
};
registerCallAction("mute", muteAction);
/** @type {CallActionDefinition} */
export const quickActionSettings = {
    condition: ({ owner, channel }) => !owner.env.inCallMenu && channel?.isSelfInCall,
    dropdown: true,
    dropdownComponent: QuickVoiceSettings,
    dropdownMenuClass: "p-1 overflow-x-hidden",
    dropdownPosition: "top-end",
    icon: "oi oi-chevron-up o-xsmaller",
    name: _t("Voice Settings"),
    sequence: 15,
    sequenceGroup: 100,
};
registerCallAction("quick-voice-settings", quickActionSettings);
registerCallAction("deafen", {
    condition: ({ owner, store, channel }) =>
        channel?.isSelfInCall && (owner.env.inCallMenu || store.rtc.selfSession?.is_deaf),
    name: ({ store }) => (store.rtc.selfSession?.is_deaf ? _t("Undeafen") : _t("Deafen")),
    isActive: ({ store }) => store.rtc.selfSession?.is_deaf,
    icon: ({ action }) => (action.isActive ? CALL_ICON_DEAFEN : "fa fa-headphones"),
    hotkey: "shift+d",
    onSelected: ({ store }) => store.rtc.toggleDeafen(),
    sequence: 10,
    sequenceGroup: 100,
    tags: ({ action }) => [
        ACTION_TAGS.CALL_ACTION_TRACKED,
        action.isActive ? ACTION_TAGS.DANGER : undefined,
    ],
});
/** @type {CallActionDefinition} */
export const cameraOnAction = {
    badge: ({ owner, store, channel }) =>
        !owner.env.inCallMenu &&
        channel?.default_display_mode === "video_full_screen" &&
        store.rtc.cameraPermission !== "granted",
    badgeIcon: "fa fa-exclamation",
    condition: ({ channel }) => channel?.isSelfInCall,
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    name: ({ store }) =>
        store.rtc?.isRemote
            ? _t("Camera is unavailable outside the call tab.")
            : store.rtc.selfSession?.is_camera_on
            ? _t("Turn camera off")
            : _t("Turn camera on"),
    isActive: ({ store }) => store.rtc.selfSession?.is_camera_on,
    icon: "fa fa-video-camera",
    onSelected: ({ action, owner, store }) =>
        store.rtc.toggleVideo("camera", { env: owner.env, rootRef: action.actionRef }),
    sequence: 10,
    sequenceGroup: 120,
    tags: ({ action, store, channel }) => {
        const tags = [ACTION_TAGS.CALL_ACTION_TRACKED];
        if (action.isActive) {
            tags.push(ACTION_TAGS.SUCCESS);
        }
        if (
            channel?.default_display_mode === "video_full_screen" &&
            store.rtc.cameraPermission !== "granted"
        ) {
            tags.push(ACTION_TAGS.DANGER, ACTION_TAGS.WARNING_BADGE);
        }
        return tags;
    },
};
registerCallAction("camera-on", cameraOnAction);
/** @type {CallActionDefinition} */
export const quickVideoSettings = {
    condition: ({ owner, channel }) => !owner.env.inCallMenu && channel?.isSelfInCall,
    dropdown: true,
    dropdownComponent: QuickVideoSettings,
    dropdownMenuClass: "p-1 overflow-x-hidden",
    dropdownPosition: "top-end",
    icon: "oi oi-chevron-up o-xsmaller",
    name: _t("Video Settings"),
    sequence: 15,
    sequenceGroup: 120,
};
registerCallAction("quick-video-settings", quickVideoSettings);
/** @type {CallActionDefinition} */
export const switchCameraAction = {
    condition: ({ channel, store }) =>
        channel?.isSelfInCall && isMobileOS() && store.rtc.selfSession?.is_camera_on,
    name: _t("Switch Camera"),
    isActive: false,
    icon: "fa fa-refresh",
    onSelected: ({ store }) => store.rtc.toggleCameraFacingMode(),
    sequence: 40,
    sequenceGroup: 100,
};
registerCallAction("switch-camera", switchCameraAction);
registerCallAction("raise-hand", {
    condition: ({ channel }) => channel?.isSelfInCall,
    name: ({ store }) => (store.rtc.selfSession?.raisingHand ? _t("Lower Hand") : _t("Raise Hand")),
    isActive: ({ store }) => store.rtc.selfSession?.raisingHand,
    icon: "fa fa-hand-paper-o",
    hotkey: "shift+h",
    onSelected: ({ store }) => store.rtc.raiseHand(!store.rtc.selfSession.raisingHand),
    sequence: 50,
    sequenceGroup: 200,
    tags: ({ action }) => [
        ACTION_TAGS.CALL_ACTION_TRACKED,
        action.isActive ? ACTION_TAGS.SUCCESS : undefined,
    ],
});
registerCallAction("share-screen", {
    condition: ({ channel }) => channel?.isSelfInCall && !isMobileOS(),
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    name: ({ store }) =>
        store.rtc?.isRemote
            ? _t("Screen sharing is unavailable outside the call tab.")
            : store.rtc.selfSession?.is_screen_sharing_on
            ? _t("Stop Sharing Screen")
            : _t("Share Screen"),
    isActive: ({ store }) => store.rtc.selfSession?.is_screen_sharing_on,
    icon: "fa fa-desktop",
    onSelected: ({ owner, store }) => store.rtc.toggleVideo("screen", { env: owner.env }),
    sequence: 40,
    sequenceGroup: 200,
    tags: ({ action }) => [
        ACTION_TAGS.CALL_ACTION_TRACKED,
        action.isActive ? ACTION_TAGS.SUCCESS : undefined,
    ],
});
registerCallAction("fullscreen", {
    condition: ({ channel, owner }) => channel?.isSelfInCall && !owner.env.pipWindow,
    name: ({ store }) => (store.rtc.isBrowserFullscreen ? _t("Exit Fullscreen") : _t("Fullscreen")),
    isActive: ({ store }) => store.rtc.isBrowserFullscreen,
    icon: ({ action }) => (action.isActive ? "fa fa-compress" : "fa fa-expand"),
    onSelected: ({ channel, store }) => {
        channel.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.DISCARDED;
        if (store.rtc.isBrowserFullscreen) {
            store.rtc.exitBrowserFullscreen();
        } else {
            store.rtc.closePip();
            store.rtc.enterFullscreen(undefined, { browserFullscreen: true });
        }
    },
    sequence: 80,
    tags: ACTION_TAGS.CALL_LAYOUT,
});
registerCallAction("picture-in-picture", {
    condition: ({ owner, channel, store }) =>
        channel?.isSelfInCall && !store.env?.isSmall && !owner.env.pipWindow,
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    name: ({ store }) =>
        store.rtc?.isPipMode ? _t("Exit Picture in Picture") : _t("Picture in Picture"),
    isActive: ({ store }) => store.rtc?.isPipMode,
    icon: "oi oi-launch",
    onSelected: ({ owner, channel, store }) => {
        channel.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.DISCARDED;
        const isPipMode = store.rtc?.isPipMode;
        if (isPipMode) {
            store.rtc.closePip();
        } else {
            store.rtc.openPip({ context: owner });
        }
    },
    sequence: 70,
    tags: ACTION_TAGS.CALL_LAYOUT,
});
registerCallAction("change-layout", {
    condition: ({ channel, owner }) =>
        channel?.isSelfInCall && !owner.env.inCallMenu && !owner.env.pipWindow,
    name: _t("Change Layout"),
    icon: "fa fa-fw fa-th-large",
    onSelected: ({ channel, store }) =>
        store.env.services.dialog.add(ChangeLayoutDialog, { channel }),
    sequence: 60,
    tags: ACTION_TAGS.CALL_LAYOUT,
});
/** @type {CallActionDefinition} */
export const acceptWithCamera = {
    condition: ({ channel }) =>
        channel?.self_member_id?.rtc_inviting_session_id?.is_camera_on &&
        typeof channel?.useCameraByDefault !== "boolean",
    disabledCondition: ({ store }) => store.rtc?.hasPendingRequest,
    name: _t("Accept with camera"),
    icon: "fa fa-video-camera",
    onSelected: ({ channel, store }) => store.rtc.toggleCall(channel, { camera: true }),
    sequence: 100,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
};
registerCallAction("accept-with-camera", acceptWithCamera);
registerCallAction("join-back", {
    btnClass: ({ owner }) =>
        attClassObjectToString({
            "text-nowrap pe-2 rounded-pill": true,
            "mx-1": !owner.env.inCallInvitation,
        }),
    condition: ({ channel }) =>
        !channel?.isSelfInCall && typeof channel?.useCameraByDefault === "boolean",
    disabledCondition: ({ store }) => store.rtc?.hasPendingRequest,
    icon: ({ channel }) => (channel.useCameraByDefault ? "fa fa-video-camera" : "fa fa-phone"),
    inlineName: ({ owner }) => (owner.env.inCallInvitation ? undefined : _t("Join")),
    name: ({ channel }) => (channel?.useCameraByDefault ? _t("Join Video Call") : _t("Join Call")),
    onSelected: ({ channel, store }) =>
        store.rtc.toggleCall(channel, { camera: channel.useCameraByDefault }),
    sequence: 110,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
});
registerCallAction("join-with-camera", {
    btnClass: "text-nowrap",
    condition: ({ channel }) =>
        !channel?.isSelfInCall &&
        !channel?.self_member_id?.rtc_inviting_session_id &&
        typeof channel?.useCameraByDefault !== "boolean",
    disabledCondition: ({ store }) => store.rtc?.hasPendingRequest,
    name: _t("Join Video Call"),
    icon: "fa fa-video-camera",
    onSelected: ({ channel, store }) => store.rtc.toggleCall(channel, { camera: true }),
    sequence: 120,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
});
/** @type {CallActionDefinition} */
export const joinAction = {
    condition: ({ channel }) =>
        !channel?.isSelfInCall && typeof channel?.useCameraByDefault !== "boolean",
    disabledCondition: ({ store }) => store.rtc?.hasPendingRequest,
    name: _t("Join Call"),
    icon: "fa fa-phone",
    onSelected: ({ channel, store }) => store.rtc.toggleCall(channel),
    sequence: 130,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
};
registerCallAction("join", joinAction);
/** @type {CallActionDefinition} */
export const rejectAction = {
    btnClass: ({ owner, channel }) =>
        attClassObjectToString({
            "pe-2 rounded-pill": typeof channel?.useCameraByDefault === "boolean",
            "mx-1": !owner.env.inCallInvitation && typeof channel?.useCameraByDefault === "boolean",
        }),
    condition: ({ channel }) => channel?.self_member_id?.rtc_inviting_session_id,
    disabledCondition: ({ store }) => store.rtc?.hasPendingRequest,
    icon: "oi oi-close",
    inlineName: ({ owner, channel }) =>
        !owner.env.inCallInvitation && typeof channel?.useCameraByDefault === "boolean"
            ? _t("Reject")
            : undefined,
    name: _t("Reject"),
    onSelected: ({ channel, store }) => {
        if (store.rtc.hasPendingRequest) {
            return;
        }
        store.rtc.leaveCall(channel);
    },
    sequence: 140,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.DANGER],
};
registerCallAction("reject", rejectAction);
registerCallAction("disconnect", {
    condition: ({ channel }) =>
        channel?.isSelfInCall && !channel?.self_member_id?.rtc_inviting_session_id,
    disabledCondition: ({ store }) => store.rtc?.hasPendingRequest,
    name: _t("Disconnect"),
    icon: "fa fa-phone",
    onSelected: ({ channel, store }) => store.rtc.toggleCall(channel),
    sequence: 150,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.DANGER],
});

export class CallAction extends Action {
    /** @type {() => import("models").DiscussChannel} */
    channelFn;

    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel|() => import("models").DiscussChannel} channel
     */
    constructor({ channel }) {
        super(...arguments);
        this.channelFn = typeof channel === "function" ? channel : () => channel;
    }

    get params() {
        const channel = this.channelFn();
        return Object.assign(super.params, { channel });
    }
}

/** @typedef {UseActions<CallActionParams, CallAction>} UseCallActions_Def */
class UseCallActions extends UseActions {
    ActionClass = CallAction;
}

/**
 * @param {import("@mail/core/common/action").ActionRootRefParam & {channel?: DiscussChannel|() => DiscussChannel}} [params0={}]
 * @return {UseCallActions_Def}
 */
export function useCallActions({ channel, rootRef } = {}) {
    return useAction(callActionsRegistry, UseCallActions, CallAction, { channel, rootRef });
}
