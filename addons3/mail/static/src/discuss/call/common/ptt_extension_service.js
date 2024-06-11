/* @odoo-module */

import { parseVersion } from "@mail/utils/common/misc";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const pttExtensionHookService = {
    start(env) {
        const INITIAL_RELEASE_TIMEOUT = 500;
        const COMMON_RELEASE_TIMEOUT = 200;
        // https://chromewebstore.google.com/detail/discuss-push-to-talk/mdiacebcbkmjjlpclnbcgiepgifcnpmg
        const EXT_ID = "mdiacebcbkmjjlpclnbcgiepgifcnpmg";
        const versionPromise =
            window.chrome?.runtime?.sendMessage(EXT_ID, { type: "ask-version" }) ??
            Promise.resolve("1.0.0.0");
        let isEnabled = false;
        let voiceActivated = false;

        browser.addEventListener("message", ({ data, origin, source }) => {
            const rtc = env.services["discuss.rtc"];
            if (
                source !== window ||
                origin !== location.origin ||
                data.from !== "discuss-push-to-talk" ||
                (!rtc && data.type !== "answer-is-enabled")
            ) {
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

        /**
         * Send a message to the PTT extension.
         *
         * @param {"ask-is-enabled" | "subscribe" | "unsubscribe" | "is-talking"} type
         * @param {*} value
         */
        async function sendMessage(type, value) {
            if (!isEnabled && type !== "ask-is-enabled") {
                return;
            }
            const version = parseVersion(await versionPromise);
            if (version.isLowerThan("1.0.0.2")) {
                window.postMessage({ from: "discuss", type, value }, location.origin);
                return;
            }
            window.chrome?.runtime?.sendMessage(EXT_ID, { type, value });
        }

        sendMessage("ask-is-enabled");

        return {
            notifyIsTalking(isTalking) {
                sendMessage("is-talking", isTalking);
            },
            subscribe() {
                sendMessage("subscribe");
            },
            unsubscribe() {
                voiceActivated = false;
                sendMessage("unsubscribe");
            },
            get isEnabled() {
                return isEnabled;
            },
        };
    },
};

registry.category("services").add("discuss.ptt_extension", pttExtensionHookService);
