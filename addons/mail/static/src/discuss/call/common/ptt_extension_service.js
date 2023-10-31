/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const pttExtensionHookService = {
    start(env) {
        const INITIAL_RELEASE_TIMEOUT = 500;
        const COMMON_RELEASE_TIMEOUT = 200;
        let voiceActivated = false;

        browser.addEventListener("message", ({ data }) => {
            const rtc = env.services["discuss.rtc"];
            if (data.from !== "discuss-push-to-talk") {
                return;
            }
            if (data.type === "push-to-talk-pressed") {
                voiceActivated = false;
                const isFirstPress = !rtc.state.selfSession?.isTalking;
                rtc.onPushToTalk();
                if (rtc.state.selfSession?.isTalking) {
                    // Second key press is slow to come thus, the first timeout
                    // must be greater than the following ones.
                    rtc.setPttReleaseTimeout(
                        isFirstPress ? INITIAL_RELEASE_TIMEOUT : COMMON_RELEASE_TIMEOUT
                    );
                }
            }
            if (data.type === "toggle-voice") {
                if (voiceActivated) {
                    rtc.setPttReleaseTimeout(0);
                } else {
                    rtc.onPushToTalk();
                }
                voiceActivated = !voiceActivated;
            }
        });

        return {
            notifyIsTalking(isTalking) {
                window.postMessage({ from: "discuss", type: "is-talking", value: isTalking });
            },
            subscribe() {
                window.postMessage({ from: "discuss", type: "subscribe" });
            },
            unsubscribe() {
                voiceActivated = false;
                window.postMessage({ from: "discuss", type: "unsubscribe" });
            },
        };
    },
};

registry.category("services").add("discuss.ptt_extension", pttExtensionHookService);
