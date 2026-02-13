import { CallSuggestionTooltip } from "@mail/discuss/call/common/call_suggestion_tooltip";
import { onChange } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";

export const MUTE_SUGGESTION_CONFIG = {
    armingDelay: 1200,
    activeDuration: 4000,
    cooldownDuration: 60000,
};

export function setupMuteSuggestion(store) {
    const rtc = store.env.services["discuss.rtc"];
    const session = rtc.selfSession;
    const popoverService = store.env.services.popover;

    if (!session || !popoverService) {
        return () => {};
    }

    const callNotificationId = "discuss_call_mute_suggestion";
    let timers = {};
    let closePopover, dismissed;

    onChange(session, ["isTalking", "is_muted"], () => {
        if (!session.is_muted) {
            cleanup();
            dismissed = undefined;
            return;
        }
        if (timers.cooldown || dismissed || closePopover) {
            return;
        }
        if (rtc.microphonePermission === "granted" && session.is_muted && session.isTalking) {
            if (!timers.arming) {
                timers.arming = setTimeout(showSuggestion, MUTE_SUGGESTION_CONFIG.armingDelay);
            }
        } else {
            if (timers.arming) {
                clearTimeout(timers.arming);
                timers.arming = null;
            }
        }
    });

    function startCooldown() {
        timers.display = setTimeout(() => {
            hideSuggestion();
            timers.display = null;
            timers.cooldown = setTimeout(() => {
                timers.cooldown = null;
            }, MUTE_SUGGESTION_CONFIG.cooldownDuration);
        }, MUTE_SUGGESTION_CONFIG.activeDuration);
    }

    function showSuggestion() {
        timers.arming = null;
        const target = document.querySelector(
            ".o-discuss-CallActionList .o-discuss-callAction-Mute"
        );
        if (target) {
            closePopover = popoverService.add(
                target,
                CallSuggestionTooltip,
                {
                    text: _t("Are you talking? Your mic is off. Click the mic to turn it on."),
                    onDismiss: () => {
                        dismissed = true;
                        cleanup();
                    },
                },
                { position: "top-middle" }
            );
        } else {
            rtc.addCallNotification({
                id: callNotificationId,
                text: _t("Are you talking? Your mic is off. Unmute to speak."),
                delay: MUTE_SUGGESTION_CONFIG.activeDuration,
            });
        }
        startCooldown();
    }

    function hideSuggestion() {
        closePopover?.();
        closePopover = undefined;
        rtc.removeCallNotification(callNotificationId);
    }

    function cleanup() {
        Object.values(timers).forEach(clearTimeout);
        timers = {};
        hideSuggestion();
    }

    return cleanup;
}
