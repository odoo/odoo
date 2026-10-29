import { parseVersion } from "@mail/utils/common/misc";

import { markup, Plugin, signal, useListener } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { services } from "@web/core/services";
import { useEnv } from "@web/owl2/utils";

const INITIAL_RELEASE_TIMEOUT = 750;
const COMMON_RELEASE_TIMEOUT = 200;
// https://chromewebstore.google.com/detail/discuss-push-to-talk/mdiacebcbkmjjlpclnbcgiepgifcnpmg
const EXT_ID = "mdiacebcbkmjjlpclnbcgiepgifcnpmg";

export class PttExtensionPlugin extends Plugin {
    /**
     * `discuss.rtc` is a legacy service that depends on this plugin: read it lazily from
     * `env.services`.
     *
     * @private
     */
    env = useEnv();
    isEnabled = signal(false);
    voiceActivated = signal(false);
    downloadURL = `https://chromewebstore.google.com/detail/discuss-push-to-talk/${EXT_ID}`;

    setup() {
        this.versionPromise =
            window.chrome?.runtime
                ?.sendMessage(EXT_ID, { type: "ask-version" })
                .catch(() => "1.0.0.0") ?? Promise.resolve("1.0.0.0");
        useListener(window, "message", (ev) => this.onMessage(ev));
        this.sendMessage("ask-is-enabled");
    }

    get downloadText() {
        return _t(
            "Push-to-Talk works only while this tab is in focus. To use it outside this tab, we recommend installing our %(anchor_start)sextension%(anchor_end)s.",
            {
                anchor_start: markup`<a href="${this.downloadURL}" target="_blank" class="text-reset text-decoration-underline">`,
                anchor_end: markup`</a>`,
            }
        );
    }

    notifyIsTalking(isTalking) {
        this.sendMessage("is-talking", isTalking);
    }

    subscribe() {
        this.sendMessage("subscribe");
    }

    unsubscribe() {
        this.voiceActivated.set(false);
        this.sendMessage("unsubscribe");
    }

    /** @param {MessageEvent} ev */
    onMessage({ data, origin, source }) {
        const rtc = this.env.services["discuss.rtc"];
        if (
            source !== window ||
            origin !== location.origin ||
            data?.from !== "discuss-push-to-talk" ||
            (!rtc && data.type !== "answer-is-enabled")
        ) {
            return;
        }
        switch (data.type) {
            case "push-to-talk-pressed":
                {
                    this.voiceActivated.set(false);
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
                    if (this.voiceActivated()) {
                        rtc.setPttReleaseTimeout(0);
                    } else {
                        rtc.onPushToTalk();
                    }
                    this.voiceActivated.set(!this.voiceActivated());
                }
                break;
            case "answer-is-enabled":
                this.isEnabled.set(true);
                break;
        }
    }

    /**
     * Send a message to the PTT extension.
     *
     * @param {"ask-is-enabled" | "subscribe" | "unsubscribe" | "is-talking"} type
     * @param {*} value
     */
    async sendMessage(type, value) {
        if (!this.isEnabled() && type !== "ask-is-enabled") {
            return;
        }
        const version = parseVersion(await this.versionPromise);
        if (location.origin === "null") {
            return;
        }
        if (version.isLowerThan("1.0.0.2")) {
            window.postMessage({ from: "discuss", type, value }, location.origin);
            return;
        }
        window.chrome?.runtime?.sendMessage(EXT_ID, { type, value });
    }
}

services.add(PttExtensionPlugin);
