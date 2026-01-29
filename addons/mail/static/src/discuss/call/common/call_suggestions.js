import { onChange } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const MUTE_SUGGESTION_CONFIG = {
    armingDelay: 1200,
    activeDuration: 6000,
    cooldownDuration: 60000,
};
export const MUTE_SUGGESTION_ID = "discuss_call_mic_speak_while_muted";

export const callSuggestionsRegistry = registry.category("discuss.call/suggestions");

/**
 * @typedef {object} CallSuggestionDefinition
 * @property {string} actionId - Target call action ID (determines which action button the suggestion anchors to).
 * @property {string} bodyText - Body text of the suggestion.
 * @property {string} headerText - Header text of the suggestion.
 * @property {string} iconClass - CSS class for the suggestion icon.
 * @property {number} [priority=10] - Display priority of the suggestion (higher values take precedence).
 * @property {function(CallSuggestionInitParams): (function(): void|undefined)} init -
 *   Called when the user joins a call (selfSession is set). Returns an optional
 *   cleanup function called when the user leaves.
 */

/**
 * @typedef {object} CallSuggestionInitParams
 * @property {string} id - The suggestion definition ID.
 * @property {function(function(): void): void} onSuggestionDismiss - Register a callback to be called when the suggestion is dismissed.
 * @property {import("@mail/discuss/call/common/rtc_service").Rtc} rtc
 * @property {import("@mail/core/store").Store} store
 * @property {import("@mail/discuss/call/common/rtc_service").CallSuggestion} suggestion - The suggestion object.
 */

/**
 * @param {string} id - Unique identifier for the suggestion.
 * @param {CallSuggestionDefinition} definition
 */
export function registerCallSuggestion(id, definition) {
    callSuggestionsRegistry.add(id, definition);
}

registerCallSuggestion("discuss_call_mic_permission_denied", {
    actionId: "mute",
    bodyText: _t("To use your microphone, allow access in your browser settings."),
    headerText: _t("No microphone access"),
    iconClass: "fa fa-microphone-slash text-warning",
    priority: 30,
    init: ({ onSuggestionDismiss, rtc, suggestion }) => {
        suggestion.isVisible = Boolean(rtc.showMicrophonePermissionWarning);
        const disposeFn = onChange(rtc, "showMicrophonePermissionWarning", () => {
            suggestion.isVisible = Boolean(rtc.showMicrophonePermissionWarning);
        });
        onSuggestionDismiss(() => {
            rtc.isMicrophonePermissionWarningDismissed = true;
        });
        return disposeFn;
    },
});

registerCallSuggestion("discuss_call_mic_muted_by_system", {
    actionId: "mute",
    bodyText: _t("Go to your computer settings to unmute your microphone and increase its volume."),
    headerText: _t("Microphone muted by system"),
    iconClass: "fa fa-microphone-slash text-warning",
    priority: 20,
    init: ({ rtc, suggestion }) =>
        onChange(rtc, "showMicrophoneSilentWarning", () => {
            suggestion.isVisible = Boolean(rtc.showMicrophoneSilentWarning);
        }),
});

registerCallSuggestion(MUTE_SUGGESTION_ID, {
    actionId: "mute",
    bodyText: _t("Your microphone is muted, unmute it to be heard."),
    headerText: _t("You seem to be talking"),
    iconClass: "fa fa-microphone-slash text-warning",
    priority: 10,
    init: ({ onSuggestionDismiss, rtc, suggestion }) => {
        const session = rtc.selfSession;
        let timers = {};
        let dismissed = false;

        if (!session) {
            return () => {};
        }

        onSuggestionDismiss(() => {
            dismissed = true;
            cleanup();
        });

        const disposeFn = onChange(session, ["isTalking", "is_muted"], () => {
            if (!session.is_muted) {
                cleanup();
                dismissed = false;
                return;
            }
            if (timers.cooldown || dismissed || suggestion.isVisible) {
                return;
            }
            if (
                rtc.microphonePermission === "granted" &&
                session.is_muted &&
                session.isTalking &&
                !timers.arming
            ) {
                timers.arming = setTimeout(showSuggestion, MUTE_SUGGESTION_CONFIG.armingDelay);
            } else {
                clearTimeout(timers.arming);
                timers.arming = null;
            }
        });

        function hideAndStartCooldown() {
            timers.autoHide = setTimeout(() => {
                suggestion.isVisible = false;
                timers.autoHide = null;
                timers.cooldown = setTimeout(() => {
                    timers.cooldown = null;
                }, MUTE_SUGGESTION_CONFIG.cooldownDuration);
            }, MUTE_SUGGESTION_CONFIG.activeDuration);
        }

        function showSuggestion() {
            timers.arming = null;
            suggestion.isVisible = true;
            hideAndStartCooldown();
        }

        function cleanup() {
            suggestion.isVisible = false;
            Object.values(timers).forEach(clearTimeout);
            timers = {};
        }

        return () => {
            cleanup();
            disposeFn();
        };
    },
});

/**
 * Called when the user joins a call. Creates suggestion objects from the registry
 * and calls each suggestion's init.
 *
 * @param {import("@mail/core/store").Store} store
 * @returns {function(): void} Cleanup function called when the user leaves the call.
 */
export function setupCallSuggestions(store) {
    const rtc = store.env.services["discuss.rtc"];
    const suggestions = callSuggestionsRegistry.getEntries();
    const cleanupFns = [];

    for (const [id, definition] of suggestions) {
        let dismissFn = () => {};
        const suggestion = rtc.addCallSuggestion(definition.actionId, {
            bodyText: definition.bodyText,
            headerText: definition.headerText,
            iconClass: definition.iconClass,
            id,
            onDismiss: () => {
                suggestion.isVisible = false;
                dismissFn();
            },
            priority: definition.priority ?? 10,
        });

        const cleanupFn = definition.init({
            id,
            onSuggestionDismiss: (fn) => (dismissFn = fn),
            rtc,
            store,
            suggestion,
        });

        cleanupFns.push(() => {
            cleanupFn?.();
            suggestion.isVisible = false;
        });
    }

    function cleanup() {
        for (const fn of cleanupFns) {
            fn();
        }
    }

    return cleanup;
}
