// @ts-check
/** @odoo-module native */
import { Action, ACTION_TAGS, UseActions } from "@mail/core/common/action";
import { attClassObjectToString } from "@mail/utils/common/format";
import { useComponent, useState } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";

import { QuickVideoSettings } from "./quick_video_settings.js";
import { QuickVoiceSettings } from "./quick_voice_settings.js";
import { CALL_PROMOTE_FULLSCREEN } from "./thread_model_patch.js";
export const callActionsRegistry = registry.category("discuss.call/actions");
export const CALL_ICON_DEAFEN = "fa-solid fa-deaf";
export const CALL_ICON_MUTED = "fa-solid fa-microphone-slash";

/** @typedef {import("@mail/model/record").Record} Record */
/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("models").Thread} Thread */
/** @typedef {(Component|Record) & { env: {inCallMenu?: boolean, inCallInvitation?: boolean}, }} CallActionOwner */
/** @typedef {import("@mail/core/common/action").ActionDefinition<CallActionOwner, ActionParams, CallAction>} ActionDefinition */
/** @typedef {import("@mail/core/common/action").ActionParams<CallActionOwner> & { action: CallAction, thread: Thread }} ActionParams */
/**
 * @typedef {Object} CallActionSpecificDefinition
 * @property {boolean} [isTracked]
 * @property {boolean|((this: CallAction, params: ActionParams) => any)} [condition=true]
 */
/** @typedef {ActionDefinition & CallActionSpecificDefinition} CallActionDefinition */
/**
 * @param {string} id
 * @param {CallActionDefinition} definition
 */
export function registerCallAction(id, definition) {
    callActionsRegistry.add(id, definition);
}

export const muteAction = {
    /** @param {ActionParams} params */
    badge: ({ owner, store }) =>
        !owner.env.inCallMenu && store.rtc.microphonePermission !== "granted",
    badgeIcon: "fa-solid fa-exclamation",
    /** @param {ActionParams} params */
    condition: ({ owner, store, thread }) =>
        thread?.isSelfInCall &&
        (owner.env.inCallMenu || !store.rtc.selfSession?.is_deaf),
    /** @param {ActionParams} params */
    name: ({ store }) => (store.rtc.selfSession.isMute ? _t("Unmute") : _t("Mute")),
    /** @param {ActionParams} params */
    isActive: ({ store }) =>
        (store.rtc.selfSession?.isMute &&
            store.rtc.microphonePermission === "granted") ||
        store.rtc.selfSession?.is_deaf,
    isTracked: true,
    /** @param {ActionParams} params */
    icon: ({ action, owner, store }) =>
        action.isActive
            ? store.rtc.selfSession?.is_deaf && !owner.env.inCallMenu
                ? CALL_ICON_DEAFEN
                : CALL_ICON_MUTED
            : "fa-solid fa-microphone",
    hotkey: "shift+m",
    /** @param {ActionParams} params */
    onSelected: ({ store }) => store.rtc.toggleMicrophone(),
    sequence: 10,
    sequenceGroup: 100,
    /** @param {ActionParams} params */
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
    /** @param {ActionParams} params */
    condition: ({ owner, thread }) => !owner.env.inCallMenu && thread?.isSelfInCall,
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
    /** @param {ActionParams} params */
    condition: ({ owner, store, thread }) =>
        thread?.isSelfInCall &&
        (owner.env.inCallMenu || store.rtc.selfSession?.is_deaf),
    /** @param {ActionParams} params */
    name: ({ store }) =>
        store.rtc.selfSession.is_deaf ? _t("Undeafen") : _t("Deafen"),
    /** @param {ActionParams} params */
    isActive: ({ store }) => store.rtc.selfSession?.is_deaf,
    isTracked: true,
    /** @param {ActionParams} params */
    icon: ({ action }) =>
        action.isActive ? CALL_ICON_DEAFEN : "fa-solid fa-headphones",
    hotkey: "shift+d",
    /** @param {ActionParams} params */
    onSelected: ({ store }) => store.rtc.toggleDeafen(),
    sequence: 10,
    sequenceGroup: 100,
    /** @param {ActionParams} params */
    tags: ({ action }) => (action.isActive ? ACTION_TAGS.DANGER : undefined),
});
export const cameraOnAction = {
    /** @param {ActionParams} params */
    badge: ({ owner, store, thread }) =>
        !owner.env.inCallMenu &&
        thread?.default_display_mode === "video_full_screen" &&
        store.rtc.cameraPermission !== "granted",
    badgeIcon: "fa-solid fa-exclamation",
    /** @param {ActionParams} params */
    condition: ({ thread }) => thread?.isSelfInCall,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    /** @param {ActionParams} params */
    name: ({ store }) =>
        store.rtc?.isRemote
            ? _t("Camera is unavailable outside the call tab.")
            : store.rtc.selfSession.is_camera_on
              ? _t("Stop camera")
              : _t("Turn camera on"),
    /** @param {ActionParams} params */
    isActive: ({ store }) => store.rtc.selfSession?.is_camera_on,
    isTracked: true,
    icon: "fa-solid fa-video",
    /** @param {ActionParams} params */
    onSelected: ({ owner, store }) =>
        store.rtc.toggleVideo("camera", { env: owner.env }),
    sequence: 10,
    sequenceGroup: 120,
    /** @param {ActionParams} params */
    tags: ({ action, store, thread }) => {
        const tags = [];
        if (action.isActive) {
            tags.push(ACTION_TAGS.SUCCESS);
        }
        if (
            thread?.default_display_mode === "video_full_screen" &&
            store.rtc.cameraPermission !== "granted"
        ) {
            tags.push(ACTION_TAGS.DANGER, ACTION_TAGS.WARNING_BADGE);
        }
        return tags;
    },
};
registerCallAction("camera-on", cameraOnAction);
export const quickVideoSettings = {
    /** @param {ActionParams} params */
    condition: ({ owner, thread }) => !owner.env.inCallMenu && thread?.isSelfInCall,
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
    /** @param {ActionParams} params */
    condition: ({ store, thread }) =>
        thread?.isSelfInCall && isMobileOS() && store.rtc.selfSession?.is_camera_on,
    name: _t("Switch Camera"),
    isActive: false,
    icon: "fa-solid fa-arrows-rotate",
    /** @param {ActionParams} params */
    onSelected: ({ store }) => store.rtc.toggleCameraFacingMode(),
    sequence: 40,
    sequenceGroup: 100,
};
registerCallAction("switch-camera", switchCameraAction);
registerCallAction("raise-hand", {
    /** @param {ActionParams} params */
    condition: ({ thread }) => thread?.isSelfInCall,
    /** @param {ActionParams} params */
    name: ({ store }) =>
        store.rtc.selfSession.raisingHand ? _t("Lower Hand") : _t("Raise Hand"),
    /** @param {ActionParams} params */
    isActive: ({ store }) => Boolean(store.rtc.selfSession?.raisingHand),
    isTracked: true,
    icon: "fa-regular fa-hand",
    /** @param {ActionParams} params */
    onSelected: ({ store }) => store.rtc.raiseHand(!store.rtc.selfSession.raisingHand),
    sequence: 50,
    sequenceGroup: 200,
});
registerCallAction("share-screen", {
    /** @param {ActionParams} params */
    condition: ({ thread }) => thread?.isSelfInCall && !isMobileOS(),
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    /** @param {ActionParams} params */
    name: ({ store }) =>
        store.rtc?.isRemote
            ? _t("Screen sharing is unavailable outside the call tab.")
            : store.rtc.selfSession.is_screen_sharing_on
              ? _t("Stop Sharing Screen")
              : _t("Share Screen"),
    isTracked: true,
    /** @param {ActionParams} params */
    isActive: ({ store }) => store.rtc.selfSession?.is_screen_sharing_on,
    icon: "fa-solid fa-desktop",
    /** @param {ActionParams} params */
    onSelected: ({ owner, store }) =>
        store.rtc.toggleVideo("screen", { env: owner.env }),
    sequence: 40,
    sequenceGroup: 200,
    /** @param {ActionParams} params */
    tags: ({ action }) => (action.isActive ? ACTION_TAGS.SUCCESS : undefined),
});
registerCallAction("auto-focus", {
    /** @param {ActionParams} params */
    condition: ({ owner, thread }) => !owner.env.inCallMenu && thread?.isSelfInCall,
    /** @param {ActionParams} params */
    name: ({ store }) =>
        store.settings.useCallAutoFocus
            ? _t("Disable speaker autofocus")
            : _t("Autofocus speaker"),
    /** @param {ActionParams} params */
    isActive: ({ store }) => store.settings?.useCallAutoFocus,
    /** @param {ActionParams} params */
    icon: ({ action }) =>
        action.isActive ? "fa-regular fa-eye" : "fa-regular fa-eye-slash",
    /** @param {ActionParams} params */
    onSelected: ({ store }) => {
        store.settings.useCallAutoFocus = !store.settings.useCallAutoFocus;
    },
    sequence: 50,
    sequenceGroup: 200,
});
registerCallAction("fullscreen", {
    /** @param {ActionParams} params */
    btnClass: ({ thread }) =>
        attClassObjectToString({
            "o-discuss-CallActionList-pulse": Boolean(
                thread.promoteFullscreen === CALL_PROMOTE_FULLSCREEN.ACTIVE,
            ),
        }),
    /** @param {ActionParams} params */
    condition: ({ thread }) => thread?.isSelfInCall,
    /** @param {ActionParams} params */
    name: ({ store }) =>
        store.rtc.state.isFullscreen ? _t("Exit Fullscreen") : _t("Fullscreen"),
    /** @param {ActionParams} params */
    isActive: ({ store }) => store.rtc.state.isFullscreen,
    /** @param {ActionParams} params */
    icon: ({ action }) =>
        action.isActive
            ? "fa-solid fa-down-left-and-up-right-to-center"
            : "fa-solid fa-up-right-and-down-left-from-center",
    /** @param {ActionParams} params */
    onSelected: ({ store, thread }) => {
        thread.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.DISCARDED;
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
    /** @param {ActionParams} params */
    condition: ({ owner, store, thread }) =>
        thread?.isSelfInCall && !store.env?.isSmall,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.isRemote,
    /** @param {ActionParams} params */
    name: ({ store }) =>
        store.rtc?.state.isPipMode
            ? _t("Exit Picture in Picture")
            : _t("Picture in Picture"),
    /** @param {ActionParams} params */
    isActive: ({ store }) => store.rtc?.state.isPipMode,
    icon: "oi oi-launch",
    /** @param {ActionParams} params */
    onSelected: ({ owner, store, thread }) => {
        thread.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.DISCARDED;
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
    /** @param {ActionParams} params */
    condition: ({ thread }) =>
        thread?.self_member_id?.rtc_inviting_session_id?.is_camera_on &&
        !thread?.hasCameraDefault,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Accept with camera"),
    icon: "fa-solid fa-video",
    /** @param {ActionParams} params */
    onSelected: ({ store, thread }) => store.rtc.toggleCall(thread, { camera: true }),
    sequence: 100,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
};
registerCallAction("accept-with-camera", acceptWithCamera);
registerCallAction("join-back", {
    /** @param {ActionParams} params */
    btnClass: ({ owner }) =>
        attClassObjectToString({
            "text-nowrap pe-2 rounded-pill": true,
            "mx-1": !owner.env.inCallInvitation,
        }),
    /** @param {ActionParams} params */
    condition: ({ thread }) => !thread?.isSelfInCall && thread?.hasCameraDefault,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    /** @param {ActionParams} params */
    icon: ({ thread }) =>
        thread.useCameraByDefault ? "fa-solid fa-video" : "fa-solid fa-phone",
    /** @param {ActionParams} params */
    inlineName: ({ owner }) => (owner.env.inCallInvitation ? undefined : _t("Join")),
    /** @param {ActionParams} params */
    name: ({ thread }) =>
        thread.useCameraByDefault ? _t("Join Video Call") : _t("Join Call"),
    /** @param {ActionParams} params */
    onSelected: ({ store, thread }) =>
        store.rtc.toggleCall(thread, { camera: thread.useCameraByDefault }),
    sequence: 110,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
});
registerCallAction("join-with-camera", {
    btnClass: "text-nowrap",
    /** @param {ActionParams} params */
    condition: ({ thread }) =>
        !thread?.isSelfInCall &&
        !thread?.self_member_id?.rtc_inviting_session_id &&
        !thread?.hasCameraDefault,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Join Video Call"),
    icon: "fa-solid fa-video",
    /** @param {ActionParams} params */
    onSelected: async ({ store, thread }) => {
        await store.rtc.toggleCall(thread, { camera: true });
        if (store.rtc.selfSession) {
            store.rtc.enterFullscreen();
        }
    },
    sequence: 120,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
});
export const joinAction = {
    /** @param {ActionParams} params */
    condition: ({ thread }) => !thread?.isSelfInCall && !thread?.hasCameraDefault,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Join Call"),
    icon: "fa-solid fa-phone",
    /**
     * @param {ActionParams} params
     * @param {Event} ev
     */
    onSelected: ({ store, thread }, ev) => store.rtc.toggleCall(thread),
    sequence: 130,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.SUCCESS],
};
registerCallAction("join", joinAction);
export const rejectAction = {
    /** @param {ActionParams} params */
    btnClass: ({ owner, thread }) =>
        attClassObjectToString({
            "pe-2 rounded-pill": thread?.hasCameraDefault,
            "mx-1": !owner.env.inCallInvitation && thread?.hasCameraDefault,
        }),
    /** @param {ActionParams} params */
    condition: ({ thread }) => thread?.self_member_id?.rtc_inviting_session_id,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    icon: "oi oi-close",
    /** @param {ActionParams} params */
    inlineName: ({ owner, thread }) =>
        !owner.env.inCallInvitation && thread?.hasCameraDefault
            ? _t("Reject")
            : undefined,
    name: _t("Reject"),
    /** @param {ActionParams} params */
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
    /** @param {ActionParams} params */
    condition: ({ thread }) =>
        thread?.isSelfInCall && !thread?.self_member_id?.rtc_inviting_session_id,
    /** @param {ActionParams} params */
    disabledCondition: ({ store }) => store.rtc?.state.hasPendingRequest,
    name: _t("Disconnect"),
    icon: "fa-solid fa-phone",
    /** @param {ActionParams} params */
    onSelected: ({ store, thread }) => store.rtc.toggleCall(thread),
    sequence: 150,
    sequenceGroup: 300,
    tags: [ACTION_TAGS.JOIN_LEAVE_CALL, ACTION_TAGS.DANGER],
});

/**
 * @param {string[]} stack
 * @param {Iterable<string>} activeIds
 * @returns {string[]}
 */
export function computeActionsStack(stack, activeIds) {
    const active = new Set(activeIds);
    const nextStack = stack.filter((id) => active.has(id));
    for (const id of active) {
        if (!nextStack.includes(id)) {
            nextStack.unshift(id);
        }
    }
    return nextStack;
}

/** @extends {Action<CallActionOwner, CallActionDefinition>} */
export class CallAction extends Action {
    /** @type {() => Thread} */
    threadFn;

    /**
     * @param {Object} options
     * @param {CallActionOwner} options.owner
     * @param {string} options.id
     * @param {CallActionDefinition} options.definition
     * @param {import("models").Store} [options.store]
     * @param {Thread|(() => Thread)} [options.thread]
     */
    constructor(options) {
        super(options);
        const { thread } = options;
        this.threadFn = typeof thread === "function" ? thread : () => thread;
    }

    get params() {
        return Object.assign(super.params, { thread: this.threadFn() });
    }

    get isTracked() {
        return this.definition.isTracked;
    }
}

/** @extends {UseActions<CallAction>} */
class UseCallActions extends UseActions {
    ActionClass = CallAction;
}

/**
 * @param {Object} [params0={}]
 * @param {Thread|(() => Thread)} [params0.thread]
 */
export function useCallActions({ thread } = {}) {
    const component = useComponent();
    const transformedActions = callActionsRegistry
        .getEntries()
        .map(
            ([id, definition]) =>
                new CallAction({ owner: component, id, definition, thread }),
        );
    return useState(
        new UseCallActions(component, transformedActions, useService("mail.store")),
    );
}
