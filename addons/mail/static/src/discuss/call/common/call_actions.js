import { useComponent, useState } from "@odoo/owl";
import { isBrowserSafari, isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const callActionsRegistry = registry.category("discuss.call/actions");

callActionsRegistry
    .add("mute", {
        condition: (component) => component.rtc,
        name: (component) => (component.rtc.syncState.isMute ? _t("Unmute") : _t("Mute")),
        isActive: (component) => component.rtc.syncState.isMute,
        inactiveIcon: "fa-microphone",
        icon: "fa-microphone-slash",
        activeClass: "text-danger",
        select: (component) => {
            if (component.rtc.syncState.isMute) {
                component.rtc.syncState.action({ isMuted: false, isDeaf: false });
            } else {
                component.rtc.syncState.action({ isMuted: true });
            }
        },
        sequence: 10,
    })
    .add("deafen", {
        condition: (component) => component.rtc,
        name: (component) => (component.rtc.syncState.isDeaf ? _t("Undeafen") : _t("Deafen")),
        isActive: (component) => component.rtc.syncState?.isDeaf,
        inactiveIcon: "fa-headphones",
        icon: "fa-deaf",
        activeClass: "text-danger",
        select: (component) =>
            component.rtc.syncState.action({ isDeaf: !component.rtc.syncState.isDeaf }),
        sequence: 20,
    })
    .add("camera-on", {
        // TODO maybe camera/screen should not be available if syncState.isRemote.
        condition: (component) => component.rtc,
        name: (component) =>
            component.rtc.syncState.isCameraOn ? _t("Stop camera") : _t("Turn camera on"),
        isActive: (component) => component.rtc.syncState.isCameraOn,
        icon: "fa-video-camera",
        activeClass: "text-success",
        select: (component) =>
            component.rtc.syncState.action({ isCameraOn: !component.rtc.syncState.isCameraOn }),
        sequence: 30,
    })
    .add("raise-hand", {
        condition: (component) => component.rtc,
        name: (component) =>
            component.rtc.syncState.raisingHand ? _t("Lower Hand") : _t("Raise Hand"),
        isActive: (component) => component.rtc.syncState.raisingHand,
        icon: "fa-hand-paper-o",
        select: (component) =>
            component.rtc.syncState.action({ raisingHand: !component.rtc.syncState.raisingHand }),
        sequence: 50,
    })
    .add("share-screen", {
        condition: (component) => component.rtc && !isMobileOS(),
        name: (component) =>
            component.rtc.syncState.isScreenSharingOn
                ? _t("Stop Sharing Screen")
                : _t("Share Screen"),
        isActive: (component) => component.rtc.syncState.isScreenSharingOn,
        icon: "fa-desktop",
        activeClass: "text-success",
        select: (component) =>
            component.rtc.syncState.action({
                isScreenSharingOn: !component.rtc.syncState.isScreenSharingOn,
            }),
        sequence: 40,
    })
    .add("blur-background", {
        condition: (component) =>
            !isBrowserSafari() && component.rtc && component.rtc.selfSession?.isCameraOn,
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
        condition: (component) => component.props && component.props.fullscreen,
        name: (component) =>
            component.props.fullscreen.isActive ? _t("Exit Fullscreen") : _t("Enter Full Screen"),
        isActive: (component) => component.props.fullscreen.isActive,
        inactiveIcon: "fa-arrows-alt",
        icon: "fa-compress",
        select: (component) => {
            if (component.props.fullscreen.isActive) {
                component.props.fullscreen.exit();
            } else {
                component.props.fullscreen.enter();
            }
        },
        sequence: 70,
    });

function transformAction(component, id, action) {
    return {
        id,
        /** Condition to display this action */
        get condition() {
            return action.condition(component);
        },
        /** Name of this action, displayed to the user */
        get name() {
            return typeof action.name === "function" ? action.name(component) : action.name;
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
