import { useComponent, useState } from "@odoo/owl";
import { isBrowserSafari, isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const callActionsRegistry = registry.category("discuss.call/actions");

callActionsRegistry
    .add("mute", {
        condition: (component) => component.rtc,
        name: (component) => (component.rtc.selfSession.isMute ? _t("Unmute") : _t("Mute")),
        isActive: (component) => component.rtc.selfSession?.isMute,
        isTracked: true,
        inactiveIcon: "fa-microphone",
        icon: "fa-microphone-slash",
        activeClass: "text-danger",
        hotkey: "shift+m",
        select: (component) => component.rtc.toggleMicrophone(),
        sequence: 10,
    })
    .add("deafen", {
        condition: (component) => component.rtc,
        name: (component) => (component.rtc.selfSession.is_deaf ? _t("Undeafen") : _t("Deafen")),
        isActive: (component) => component.rtc.selfSession?.is_deaf,
        isTracked: true,
        inactiveIcon: "fa-headphones",
        icon: "fa-deaf",
        activeClass: "text-danger",
        hotkey: "shift+d",
        select: (component) => component.rtc.toggleDeafen(),
        sequence: 20,
    })
    .add("camera-on", {
        condition: (component) => component.rtc,
        available: (component) => !component.rtc?.isRemote,
        name: (component) => {
            if (component.rtc?.isRemote) {
                return _t("Camera is unavailable outside the call tab.");
            }
            return component.rtc.selfSession.is_camera_on
                ? _t("Stop camera")
                : _t("Turn camera on");
        },
        isActive: (component) => component.rtc.selfSession?.is_camera_on,
        isTracked: true,
        icon: "fa-video-camera",
        activeClass: "text-success",
        select: (component) => component.rtc.toggleVideo("camera", { env: component.env }),
        sequence: 30,
    })
    .add("switch-camera", {
        condition: (component) => isMobileOS() && component.rtc.selfSession?.is_camera_on,
        name: _t("Switch Camera"),
        isActive: () => false,
        icon: "fa-refresh",
        select: (component) => component.rtc.toggleCameraFacingMode(),
        sequence: 40,
    })
    .add("raise-hand", {
        condition: (component) => component.rtc,
        name: (component) =>
            component.rtc.selfSession.raisingHand ? _t("Lower Hand") : _t("Raise Hand"),
        isActive: (component) => component.rtc.selfSession?.raisingHand,
        isTracked: true,
        icon: "fa-hand-paper-o",
        select: (component) => component.rtc.raiseHand(!component.rtc.selfSession.raisingHand),
        sequence: 50,
    })
    .add("share-screen", {
        condition: (component) => component.rtc && !isMobileOS(),
        available: (component) => !component.rtc?.isRemote,
        name: (component) => {
            if (component.rtc?.isRemote) {
                return _t("Screen sharing is unavailable outside the call tab.");
            }
            return component.rtc.selfSession.is_screen_sharing_on
                ? _t("Stop Sharing Screen")
                : _t("Share Screen");
        },
        isTracked: true,
        isActive: (component) => component.rtc.selfSession?.is_screen_sharing_on,
        icon: "fa-desktop",
        activeClass: "text-success",
        select: (component) => component.rtc.toggleVideo("screen", { env: component.env }),
        sequence: 40,
    })
    .add("blur-background", {
        condition: (component) =>
            !isBrowserSafari() &&
            component.rtc &&
            component.rtc.selfSession?.is_camera_on &&
            component.rtc?.isHost,
        name: (component) =>
            component.store.settings.useBlur ? _t("Remove Blur") : _t("Blur Background"),
        isActive: (component) => component.store?.settings?.useBlur,
        icon: "fa-photo",
        select: (component) => {
            component.store.settings.useBlur = !component.store.settings.useBlur;
        },
        sequence: 60,
    })
    .add("fullscreen", {
        condition: (component) => Boolean(component.rtc),
        name: (component) =>
            component.rtc.state.isFullscreen ? _t("Exit Fullscreen") : _t("Fullscreen"),
        isActive: (component) => component.rtc.state.isFullscreen,
        inactiveIcon: "fa-arrows-alt",
        icon: "fa-compress",
        select: (component) => {
            if (component.rtc.state.isFullscreen) {
                component.rtc.exitFullscreen();
            } else {
                component.rtc.closePip();
                component.rtc.enterFullscreen();
            }
        },
        sequence: 70,
    })
    .add("picture-in-picture", {
        condition: (component) => component.pipService && component.rtc && !component.env?.isSmall,
        available: (component) => !component.rtc?.isRemote,
        name: (component) => {
            if (component.rtc?.state.isPipMode) {
                return _t("Exit Picture in Picture");
            } else {
                return _t("Picture in Picture");
            }
        },
        isActive: (component) => component.rtc?.state.isPipMode,
        icon: "oi-launch",
        select: (component) => {
            const isPipMode = component.rtc?.state.isPipMode;
            if (isPipMode) {
                component.rtc.closePip();
            } else {
                component.rtc.openPip({ context: component });
            }
        },
        sequence: 80,
    });

function transformAction(component, id, action) {
    return {
        id,
        /** Condition to display this action */
        get condition() {
            return action.condition(component);
        },
        get available() {
            return action.available?.(component) ?? true;
        },
        /** Name of this action, displayed to the user */
        get name() {
            return typeof action.name === "function" ? action.name(component) : action.name;
        },
        get hotkey() {
            return typeof action.hotkey === "function" ? action.hotkey(component) : action.hotkey;
        },
        get isActive() {
            return action.isActive(component);
        },
        inactiveIcon: action.inactiveIcon,
        /** Icon for the button of this action */
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        activeClass: action.activeClass,
        /**  Action to execute when this action is selected */
        select() {
            action.select(component);
        },
        /** Determines the order of this action (smaller first) */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
    };
}

export function useCallActions() {
    const component = useComponent();
    const state = useState({ actions: [] });
    state.actions = callActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
    return {
        get actions() {
            return state.actions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
        },
    };
}
