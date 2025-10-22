import { Action, ACTION_TAGS, UseActions } from "@mail/core/common/action";
import { useComponent, useState } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { QuickVoiceSettings } from "./quick_voice_settings";
import { QuickVideoSettings } from "./quick_video_settings";
import { attClassObjectToString } from "@mail/utils/common/format";
import { CALL_PROMOTE_FULLSCREEN } from "./thread_model_patch";

export const callActionsRegistry = registry.category("discuss.call/actions");

/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */

/**
 * @typedef {Object} CallActionSpecificDefinition
 * @property {boolean} [isTracked]
 */

/**
 * @typedef {ActionDefinition & CallActionSpecificDefinition} CallActionDefinition
 */

/**
 * @param {string} id
 * @param {CallActionDefinition} definition
 */
export function registerCallAction(id, definition) {
    callActionsRegistry.add(id, definition);
}

export const muteAction = {
    badge: ({ store }) => store.rtc.microphonePermission !== "granted",
    badgeIcon: "fa fa-exclamation",
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel),
    name: ({ store }) => (store.rtc.selfSession.isMute ? _t("Unmute") : _t("Mute")),
    isActive: ({ store }) =>
        (store.rtc.selfSession?.isMute && store.rtc.microphonePermission === "granted") ||
        store.rtc.selfSession?.is_deaf,
    isTracked: true,
    icon: ({ action, store }) =>
        action.isActive
            ? store.rtc.selfSession?.is_deaf
                ? "fa fa-deaf"
                : "fa fa-microphone-slash"
            : "fa fa-microphone",
    hotkey: "shift+m",
    onSelected: ({ store }) => store.rtc.toggleMicrophone(),
    sequence: 10,
    sequenceGroup: 100,
    tags: ({ action, store }) => {
        const tags = [];
        if (action.isActive) {
            tags.push(ACTION_TAGS.DANGER);
        }
        if (store.rtc.microphonePermission !== "granted") {
            tags.push(ACTION_TAGS.DANGER, ACTION_TAGS.WARNING_BADGE);
        }
        return tags;
    },
};
registerCallAction("mute", muteAction);
export const quickActionSettings = {
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel),
    dropdown: true,
    dropdownComponent: QuickVoiceSettings,
    dropdownMenuClass: "p-2",
    dropdownPosition: "top-end",
    icon: "oi oi-chevron-up o-xsmaller",
    name: _t("Voice Settings"),
    sequence: 15,
    sequenceGroup: 100,
};
registerCallAction("quick-voice-settings", quickActionSettings);
registerCallAction("deafen", {
    condition: false,
    name: ({ store }) => (store.rtc.selfSession.is_deaf ? _t("Undeafen") : _t("Deafen")),
    isActive: ({ store }) => store.rtc.selfSession?.is_deaf,
    isTracked: true,
    icon: ({ action }) => (action.isActive ? "fa fa-deaf" : "fa fa-headphones"),
    hotkey: "shift+d",
    onSelected: ({ store }) => store.rtc.toggleDeafen(),
    sequence: 10,
    sequenceGroup: 110,
    tags: ({ action }) => (action.isActive ? ACTION_TAGS.DANGER : undefined),
});
export const cameraOnAction = {
    badge: ({ store }) => store.rtc.cameraPermission !== "granted",
    badgeIcon: "fa fa-exclamation",
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel),
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    name: ({ store }) =>
        store.rtc?.isRemote
            ? _t("Camera is unavailable outside the call tab.")
            : store.rtc.selfSession.is_camera_on
            ? _t("Stop camera")
            : _t("Turn camera on"),
    isActive: ({ store }) => store.rtc.selfSession?.is_camera_on,
    isTracked: true,
    icon: "fa fa-video-camera",
    onSelected: ({ owner, store }) => store.rtc.toggleVideo("camera", { env: owner.env }),
    sequence: 10,
    sequenceGroup: 120,
    tags: ({ action, store }) => {
        const tags = [];
        if (action.isActive) {
            tags.push(ACTION_TAGS.SUCCESS);
        }
        if (store.rtc.cameraPermission !== "granted") {
            tags.push(ACTION_TAGS.DANGER, ACTION_TAGS.WARNING_BADGE);
        }
        return tags;
    },
};
registerCallAction("camera-on", cameraOnAction);
export const quickVideoSettings = {
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel),
    dropdown: true,
    dropdownComponent: QuickVideoSettings,
    dropdownMenuClass: "p-2",
    dropdownPosition: "top-end",
    icon: "oi oi-chevron-up o-xsmaller",
    name: _t("Video Settings"),
    sequence: 15,
    sequenceGroup: 120,
};
registerCallAction("quick-video-settings", quickVideoSettings);
export const switchCameraAction = {
    condition: ({ store, thread }) =>
        thread?.eq(store.rtc?.channel) && isMobileOS() && store.rtc.selfSession?.is_camera_on,
    name: _t("Switch Camera"),
    isActive: false,
    icon: "fa fa-refresh",
    onSelected: ({ store }) => store.rtc.toggleCameraFacingMode(),
    sequence: 40,
    sequenceGroup: 100,
};
registerCallAction("switch-camera", switchCameraAction);
registerCallAction("raise-hand", {
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel),
    name: ({ store }) => (store.rtc.selfSession.raisingHand ? _t("Lower Hand") : _t("Raise Hand")),
    isActive: ({ store }) => store.rtc.selfSession?.raisingHand,
    isTracked: true,
    icon: "fa fa-hand-paper-o",
    onSelected: ({ store }) => store.rtc.raiseHand(!store.rtc.selfSession.raisingHand),
    sequence: 50,
    sequenceGroup: 200,
});
registerCallAction("share-screen", {
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel) && !isMobileOS(),
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    name: ({ store }) =>
        store.rtc?.isRemote
            ? _t("Screen sharing is unavailable outside the call tab.")
            : store.rtc.selfSession.is_screen_sharing_on
            ? _t("Stop Sharing Screen")
            : _t("Share Screen"),
    isTracked: true,
    isActive: ({ store }) => store.rtc.selfSession?.is_screen_sharing_on,
    icon: "fa fa-desktop",
    onSelected: ({ owner, store }) => store.rtc.toggleVideo("screen", { env: owner.env }),
    sequence: 40,
    sequenceGroup: 200,
    tags: ({ action }) => (action.isActive ? ACTION_TAGS.SUCCESS : undefined),
});
registerCallAction("auto-focus", {
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel),
    name: ({ store }) =>
        store.settings.useCallAutoFocus ? _t("Disable speaker autofocus") : _t("Autofocus speaker"),
    isActive: ({ store }) => store.settings?.useCallAutoFocus,
    icon: ({ action }) => (action.isActive ? "fa fa-eye" : "fa fa-eye-slash"),
    onSelected: ({ store }) => (store.settings.useCallAutoFocus = !store.settings.useCallAutoFocus),
    sequence: 50,
    sequenceGroup: 200,
});
/** @deprecated Blur background action is replaced by @see QuickVideoSettings menu item "Blur background" */
export const blurBackgroundAction = {
    condition: false,
    name: ({ store }) => (store.settings.useBlur ? _t("Remove Blur") : _t("Blur Background")),
    isActive: ({ store }) => store?.settings?.useBlur,
    icon: "fa fa-photo",
    onSelected: ({ store }) => (store.settings.useBlur = !store.settings.useBlur),
    sequence: 60,
    sequenceGroup: 200,
};
registerCallAction("fullscreen", {
    btnClass: ({ owner, thread }) =>
        attClassObjectToString({
            "o-discuss-CallActionList-pulse": Boolean(
                !owner.env.pipWindow && thread.promoteFullscreen === CALL_PROMOTE_FULLSCREEN.ACTIVE
            ),
        }),
    condition: ({ store, thread }) => thread?.eq(store.rtc?.channel),
    name: ({ store }) => (store.rtc.state.isFullscreen ? _t("Exit Fullscreen") : _t("Fullscreen")),
    isActive: ({ store }) => store.rtc.state.isFullscreen,
    icon: ({ action }) => (action.isActive ? "fa fa-compress" : "fa fa-expand"),
    onSelected: ({ store }) => {
        if (store.rtc.state.isFullscreen) {
            store.rtc.exitFullscreen();
        } else {
            store.rtc.closePip();
            store.rtc.enterFullscreen();
        }
    },
    sequence: 80,
    tags: ACTION_TAGS.CALL_LAYOUT,
});
registerCallAction("picture-in-picture", {
    condition: ({ store, thread }) =>
        thread?.eq(store.rtc?.channel) &&
        store.env.services["discuss.pip_service"] &&
        !store.env?.isSmall,
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    name: ({ store }) =>
        store.rtc?.state.isPipMode ? _t("Exit Picture in Picture") : _t("Picture in Picture"),
    isActive: ({ store }) => store.rtc?.state.isPipMode,
    icon: "oi oi-launch",
    onSelected: ({ owner, store }) => {
        const isPipMode = store.rtc?.state.isPipMode;
        if (isPipMode) {
            store.rtc.closePip();
        } else {
            store.rtc.openPip({ context: owner });
        }
    },
    sequence: 70,
    tags: ACTION_TAGS.CALL_LAYOUT,
});
export const acceptWithCamera = {
    condition: ({ thread }) =>
        thread?.self_member_id?.rtc_inviting_session_id?.is_camera_on &&
        typeof thread?.useCameraByDefault !== "boolean",
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Accept with camera"),
    icon: "fa fa-video-camera",
    onSelected: ({ store, thread }) => store.rtc.toggleCall(thread, { camera: true }),
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
    condition: ({ store, thread }) =>
        !thread?.eq(store.rtc?.channel) && typeof thread?.useCameraByDefault === "boolean",
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    icon: ({ thread }) => (thread.useCameraByDefault ? "fa fa-video-camera" : "fa fa-phone"),
    inlineName: ({ owner }) => (owner.env.inCallInvitation ? undefined : _t("Join")),
    name: ({ thread }) => (thread.useCameraByDefault ? _t("Join Video Call") : _t("Join Call")),
    onSelected: ({ store, thread }) =>
        store.rtc.toggleCall(thread, { camera: thread.useCameraByDefault }),
    sequence: 110,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
});
registerCallAction("join-with-camera", {
    btnClass: "text-nowrap",
    condition: ({ store, thread }) =>
        !thread?.eq(store.rtc?.channel) &&
        !thread?.self_member_id?.rtc_inviting_session_id &&
        typeof thread?.useCameraByDefault !== "boolean",
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Join Video Call"),
    icon: "fa fa-video-camera",
    onSelected: ({ store, thread }) => store.rtc.toggleCall(thread, { camera: true }),
    sequence: 120,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
});
export const joinAction = {
    condition: ({ store, thread }) =>
        !thread?.eq(store.rtc?.channel) && typeof thread?.useCameraByDefault !== "boolean",
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Join Call"),
    icon: "fa fa-phone",
    onSelected: ({ store, thread }, ev) => store.rtc.toggleCall(thread),
    sequence: 130,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
};
registerCallAction("join", joinAction);
export const rejectAction = {
    btnClass: ({ owner, thread }) =>
        attClassObjectToString({
            "pe-2 rounded-pill": typeof thread?.useCameraByDefault === "boolean",
            "mx-1": !owner.env.inCallInvitation && typeof thread?.useCameraByDefault === "boolean",
        }),
    condition: ({ thread }) => thread?.self_member_id?.rtc_inviting_session_id,
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    icon: "oi oi-close",
    inlineName: ({ owner, thread }) =>
        !owner.env.inCallInvitation && typeof thread?.useCameraByDefault === "boolean"
            ? _t("Reject")
            : undefined,
    name: _t("Reject"),
    onSelected: ({ store, thread }) => {
        if (store.rtc.state.hasPendingRequest) {
            return;
        }
        store.rtc.leaveCall(thread);
    },
    sequence: 140,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.DANGER],
};
registerCallAction("reject", rejectAction);
registerCallAction("disconnect", {
    condition: ({ store, thread }) =>
        thread?.eq(store.rtc?.channel) && !thread?.self_member_id?.rtc_inviting_session_id,
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Disconnect"),
    icon: "fa fa-phone",
    onSelected: ({ store, thread }) => store.rtc.toggleCall(thread),
    sequence: 150,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.DANGER],
});

export class CallAction extends Action {
    /** @type {() => Thread} */
    threadFn;

    /**
     * @param {Object} param0
     * @param {Thread|() => Thread} thread
     */
    constructor({ thread }) {
        super(...arguments);
        this.threadFn = typeof thread === "function" ? thread : () => thread;
    }

    get params() {
        return Object.assign(super.params, { thread: this.threadFn() });
    }

    get isTracked() {
        return this.definition.isTracked;
    }
}

class UseCallActions extends UseActions {
    ActionClass = CallAction;
}

/**
 * @param {Object} [params0={}]
 * @param {Thread|() => Thread} thread
 */
export function useCallActions({ thread } = {}) {
    const component = useComponent();
    const transformedActions = callActionsRegistry
        .getEntries()
        .map(([id, definition]) => new CallAction({ owner: component, id, definition, thread }));
    return useState(new UseCallActions(component, transformedActions, useService("mail.store")));
}
