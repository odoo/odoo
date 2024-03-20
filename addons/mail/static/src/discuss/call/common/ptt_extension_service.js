import { markup } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { escape, sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

export const pttExtensionHookService = {
    start(env) {
        const INITIAL_RELEASE_TIMEOUT = 500;
        const COMMON_RELEASE_TIMEOUT = 200;
        let isEnabled = false;
        let voiceActivated = false;

        browser.addEventListener("message", ({ data }) => {
            const rtc = env.services["discuss.rtc"];
            if (
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
            downloadURL:
                "https://chromewebstore.google.com/detail/discuss-push-to-talk/mdiacebcbkmjjlpclnbcgiepgifcnpmg",
            get downloadText() {
                const translation = _t(
                    `The Push-to-Talk feature is only accessible within tab focus. To enable the Push-to-Talk functionality outside of this tab, we recommend downloading our %(anchor_start)sextension%(anchor_end)s.`
                );
                return markup(
                    sprintf(escape(translation), {
                        anchor_start: `<a href="${this.downloadURL}" target="_blank" class="text-reset text-decoration-underline">`,
                        anchor_end: "</a>",
                    })
                );
            },
        };
    },
};

registry.category("services").add("discuss.ptt_extension", pttExtensionHookService);
