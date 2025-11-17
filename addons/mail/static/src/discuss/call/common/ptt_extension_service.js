import { markup, reactive } from "@odoo/owl";

import { parseVersion } from "@mail/utils/common/misc";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/** In object so it's patchable */
export const pttExtensionServiceInternal = {
    onAnswerIsEnabled(pttService) {
        pttService.isEnabled = true;
    },
};

export const pttExtensionHookService = {
    start(env) {
        const INITIAL_RELEASE_TIMEOUT = 750;
        const COMMON_RELEASE_TIMEOUT = 200;
        // https://chromewebstore.google.com/detail/discuss-push-to-talk/mdiacebcbkmjjlpclnbcgiepgifcnpmg
        const EXT_ID = "mdiacebcbkmjjlpclnbcgiepgifcnpmg";
        const versionPromise =
            window.chrome?.runtime
                ?.sendMessage(EXT_ID, { type: "ask-version" })
                .catch(() => "1.0.0.0") ?? Promise.resolve("1.0.0.0");
        const self = reactive({
            isEnabled: undefined,
            voiceActivated: undefined,
            notifyIsTalking(isTalking) {
                sendMessage("is-talking", isTalking);
            },
            subscribe() {
                sendMessage("subscribe");
            },
            unsubscribe() {
                self.voiceActivated = false;
                sendMessage("unsubscribe");
            },
            downloadURL: `https://chromewebstore.google.com/detail/discuss-push-to-talk/${EXT_ID}`,
            get downloadText() {
                return _t(
                    "The Push-to-Talk feature is only accessible within tab focus. To enable the Push-to-Talk functionality outside of this tab, we recommend downloading our %(anchor_start)sextension%(anchor_end)s.",
                    {
                        anchor_start: markup`<a href="${this.downloadURL}" target="_blank" class="text-reset text-decoration-underline">`,
                        anchor_end: markup`</a>`,
                    }
                );
            },
        });

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
                        self.voiceActivated = false;
                        const isFirstPress = !rtc.selfSession?.isTalking;
                        rtc.onPushToTalk();
                        if (rtc.selfSession?.isTalking) {
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
                        if (self.voiceActivated) {
                            rtc.setPttReleaseTimeout(0);
                        } else {
                            rtc.onPushToTalk();
                        }
                        self.voiceActivated = !self.voiceActivated;
                    }
                    break;
                case "answer-is-enabled":
                    pttExtensionServiceInternal.onAnswerIsEnabled(self);
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
            if (!self.isEnabled && type !== "ask-is-enabled") {
                return;
            }
            const version = parseVersion(await versionPromise);
            if (location.origin === "null") {
                return;
            }
            if (version.isLowerThan("1.0.0.2")) {
                window.postMessage({ from: "discuss", type, value }, location.origin);
                return;
            }
            window.chrome?.runtime?.sendMessage(EXT_ID, { type, value });
        }

        sendMessage("ask-is-enabled");

        return self;
    },
};

registry.category("services").add("discuss.ptt_extension", pttExtensionHookService);
