/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const pttExtensionHookService = {
    start(env) {
        const INITIAL_RELEASE_TIMEOUT = 500;
        const COMMON_RELEASE_TIMEOUT = 200;
        let isEnabled = false;
        let voiceActivated = false;

        browser.addEventListener("message", ({ data }) => {
            const rtc = env.services["discuss.rtc"];
            if (data.from !== "discuss-push-to-talk" || !rtc) {
                return;
            }
            switch (data.type) {
                case "push-to-talk-pressed":
                    {
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
                    break;
                case "toggle-voice":
                    {
                        if (voiceActivated) {
                            rtc.setPttReleaseTimeout(0);
                        } else {
                            rtc.onPushToTalk();
                        }
                        voiceActivated = !voiceActivated;
                    }
                    break;
                case "answer-is-enabled":
                    isEnabled = true;
                    break;
            }
        });
        window.postMessage({ from: "discuss", type: "ask-is-enabled" });

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
            get isEnabled() {
                return isEnabled;
            },
        };
    },
};

registry.category("services").add("discuss.ptt_extension", pttExtensionHookService);
