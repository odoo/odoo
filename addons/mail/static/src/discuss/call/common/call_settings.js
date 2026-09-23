// @ts-check
/** @odoo-module native */
import { ActionPanel } from "@mail/core/common/action_panel";
import { DeviceSelect } from "@mail/discuss/call/common/device_select";
import { useMicrophoneVolume } from "@mail/utils/common/hooks";
import { Component, onWillStart, useExternalListener, useState, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog";

const log = makeLogger("mail.rtc.settings");
export class CallSettings extends Component {
    static template = "discuss.CallSettings";
    static props = ["withActionPanel?", "*"];
    static defaultProps = {
        withActionPanel: true,
    };
    static components = { ActionPanel, DeviceSelect };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.microphoneVolume = useMicrophoneVolume();
        this.state = useState({
            userDevices: [],
        });
        this.pttExtService = useService("discuss.ptt_extension");
        useExternalListener(
            browser,
            "keydown",
            /** @type {EventListener} */ (this._onKeyDown),
            { capture: true },
        );
        useExternalListener(
            browser,
            "keyup",
            /** @type {EventListener} */ (this._onKeyUp),
            { capture: true },
        );
        onWillStart(async () => {
            if (!browser.navigator.mediaDevices) {
                log.logic("media devices unavailable");
                this.notification.add(
                    _t("Media devices unobtainable. SSL might not be set up properly."),
                    { type: "warning" },
                );
                console.warn(
                    "Media devices unobtainable. SSL might not be set up properly.",
                );
                return;
            }
            this.state.userDevices =
                await browser.navigator.mediaDevices.enumerateDevices();
        });
    }

    get stopText() {
        return _t("Stop");
    }

    get testText() {
        return _t("Test");
    }

    get pushToTalkKeyText() {
        const { shiftKey, ctrlKey, altKey, key } =
            this.store.settings.pushToTalkKeyFormat();
        /**
         * @param {boolean} k
         * @param {string} name
         */
        const f = (k, name) => (k ? name : "");
        const keys = [
            f(ctrlKey, "Ctrl"),
            f(altKey, "Alt"),
            f(shiftKey, "Shift"),
            key,
        ].filter(Boolean);
        return keys.join(" + ");
    }

    get isMobileOS() {
        return isMobileOS();
    }

    /** @param {KeyboardEvent} ev */
    _onKeyDown(ev) {
        if (!this.store.settings.isRegisteringKey) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.store.settings.setPushToTalkKey(ev);
    }

    /** @param {KeyboardEvent} ev */
    _onKeyUp(ev) {
        if (!this.store.settings.isRegisteringKey) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.store.settings.isRegisteringKey = false;
    }

    /** @param {Event} ev */
    onChangeLogRtc(ev) {
        this.store.settings.logRtc = /** @type {HTMLInputElement} */ (
            ev.target
        ).checked;
        log.logic("onChangeLogRtc", () => ({ logRtc: this.store.settings.logRtc }));
    }

    /** @param {Event} ev */
    onChangeSelectAudioInput(ev) {
        this.store.settings.setAudioInputDevice(
            /** @type {HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement} */ (
                ev.target
            ).value,
        );
    }

    onClickDownloadLogs() {
        log.logic("onClickDownloadLogs");
        this.rtc.dumpLogs({ download: true });
    }

    onClickRegisterKeyButton() {
        this.store.settings.isRegisteringKey = !this.store.settings.isRegisteringKey;
        log.logic("onClickRegisterKeyButton", () => ({
            isRegisteringKey: this.store.settings.isRegisteringKey,
        }));
    }

    /** @param {Event} ev */
    onChangeDelay(ev) {
        this.store.settings.setDelayValue(
            /** @type {HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement} */ (
                ev.target
            ).value,
        );
    }

    /** @param {Event} ev */
    onChangeBlur(ev) {
        this.store.settings.setUseBlur(
            /** @type {HTMLInputElement} */ (ev.target).checked,
        );
    }

    /** @param {Event} ev */
    onChangeShowOnlyVideo(ev) {
        const showOnlyVideo = /** @type {HTMLInputElement} */ (ev.target).checked;
        log.logic("onChangeShowOnlyVideo", () => ({ showOnlyVideo }));
        this.store.settings.setShowOnlyVideo(showOnlyVideo);
        const activeRtcSessions = this.store.allActiveRtcSessions;
        if (showOnlyVideo && activeRtcSessions) {
            activeRtcSessions
                .filter((rtcSession) => !rtcSession.hasVideo)
                .forEach((rtcSession) => {
                    rtcSession.channel.activeRtcSession = undefined;
                });
        }
    }

    /** @param {Event} ev */
    onChangeThreshold(ev) {
        this.store.settings.setThresholdValue(
            Number(/** @type {HTMLInputElement} */ (ev.target).value),
        );
    }

    /** @param {Event} ev */
    onChangeBackgroundBlurAmount(ev) {
        this.store.settings.setBackgroundBlurAmount(
            Number(/** @type {HTMLInputElement} */ (ev.target).value),
        );
    }

    /** @param {Event} ev */
    onChangeEdgeBlurAmount(ev) {
        this.store.settings.setEdgeBlurAmount(
            Number(/** @type {HTMLInputElement} */ (ev.target).value),
        );
    }
}

export class CallSettingsDialog extends Component {
    static template = xml`
        <Dialog size="this.medium" footer="false" title.translate="Voice &amp; Video Settings">
            <CallSettings withActionPanel="false"/>
        </Dialog>
    `;
    static props = ["*"];
    static components = { CallSettings, Dialog };
}
