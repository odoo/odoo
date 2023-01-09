/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

/**
 * This model defines a "Throttle", which is an abstraction to throttle calls on a
 * provided function. Such throttled calls can be cleared, i.e it can simply stop
 * cooling down phase and clear pending func invocation. This allows having throttled
 * calls most of the time, and a few priviledged exception to immediately make the call
 * are re-trigger a cooldown like a fresh throttle call.
 */
Model({
    name: "Throttle",
    identifyingMode: "xor",
    recordMethods: {
        /**
         * Clear any buffered function call and immediately terminates any cooling
         * down phase in progress.
         */
        clear() {
            this.update({
                cooldownTimer: clear(),
                shouldInvoke: false,
            });
        },
        async do() {
            if (!this.cooldownTimer) {
                this.func();
                this.update({ cooldownTimer: {} });
            } else {
                this.update({ shouldInvoke: true });
            }
        },
        onTimeout() {
            if (this.shouldInvoke) {
                this.func();
            }
            this.update({
                cooldownTimer: clear(),
                shouldInvoke: false,
            });
        },
    },
    fields: {
        cooldownTimer: one("Timer", { inverse: "throttleOwner" }),
        /**
         * Duration, in milliseconds, of the cool down phase.
         */
        duration: attr({
            required: true,
            compute() {
                if (this.emojiGridViewAsOnScroll) {
                    return 150;
                }
                if (this.messageListViewAsScroll) {
                    return 100;
                }
                if (this.threadAsThrottleNotifyCurrentPartnerTypingStatus) {
                    return 2.5 * 1000;
                }
                if (this.messagingAsUpdateImStatusRegister) {
                    return 10 * 1000;
                }
                return clear();
            },
        }),
        emojiGridViewAsOnScroll: one("EmojiGridView", {
            identifying: true,
            inverse: "onScrollThrottle",
        }),
        /**
         * Inner function to be invoked and throttled.
         */
        func: attr(),
        messageListViewAsScroll: one("MessageListView", {
            identifying: true,
            inverse: "scrollThrottle",
        }),
        messagingAsUpdateImStatusRegister: one("Messaging", {
            identifying: true,
            inverse: "updateImStatusRegisterThrottle",
        }),
        shouldInvoke: attr({ default: false }),
        threadAsThrottleNotifyCurrentPartnerTypingStatus: one("Thread", {
            identifying: true,
            inverse: "throttleNotifyCurrentPartnerTypingStatus",
        }),
    },
});
