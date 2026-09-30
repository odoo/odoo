import { Component, onWillStart, useExternalListener, useState, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { useMicrophoneVolume } from "@mail/utils/common/hooks";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { DeviceSelect } from "@mail/discuss/call/common/device_select";
import { Dialog } from "@web/core/dialog/dialog";

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
        this.saveBackgroundBlurAmount = debounce(() => {
            browser.localStorage.setItem(
                "mail_user_setting_background_blur_amount",
                this.store.settings.backgroundBlurAmount.toString()
            );
        }, 2000);
        this.saveEdgeBlurAmount = debounce(() => {
            browser.localStorage.setItem(
                "mail_user_setting_edge_blur_amount",
                this.store.settings.edgeBlurAmount.toString()
            );
        }, 2000);
        useExternalListener(browser, "keydown", this._onKeyDown, { capture: true });
        useExternalListener(browser, "keyup", this._onKeyUp, { capture: true });
        onWillStart(async () => {
            if (!browser.navigator.mediaDevices) {
                // zxing-js: isMediaDevicesSuported or canEnumerateDevices is false.
                this.notification.add(
                    _t("Media devices unobtainable. SSL might not be set up properly."),
                    { type: "warning" }
                );
                console.warn("Media devices unobtainable. SSL might not be set up properly.");
                return;
            }
            this.state.userDevices = await browser.navigator.mediaDevices.enumerateDevices();
        });
    }

    get stopText() {
        return _t("Stop");
    }

    get testText() {
        return _t("Test");
    }

    get pushToTalkKeyText() {
        const { shiftKey, ctrlKey, altKey, key } = this.store.settings.pushToTalkKeyFormat();
        const f = (k, name) => (k ? name : "");
        const keys = [f(ctrlKey, "Ctrl"), f(altKey, "Alt"), f(shiftKey, "Shift"), key].filter(
            Boolean
        );
        return keys.join(" + ");
    }

    get isMobileOS() {
        return isMobileOS();
    }

    _onKeyDown(ev) {
        if (!this.store.settings.isRegisteringKey) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.store.settings.setPushToTalkKey(ev);
    }

    _onKeyUp(ev) {
        if (!this.store.settings.isRegisteringKey) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.store.settings.isRegisteringKey = false;
    }

    onChangeLogRtc(ev) {
        this.store.settings.logRtc = ev.target.checked;
    }

    onChangeSelectAudioInput(ev) {
        this.store.settings.setAudioInputDevice(ev.target.value);
    }

    onClickDownloadLogs() {
        this.rtc.dumpLogs({ download: true });
    }

    onClickRegisterKeyButton() {
        this.store.settings.isRegisteringKey = !this.store.settings.isRegisteringKey;
    }

    onChangeDelay(ev) {
        this.store.settings.setDelayValue(ev.target.value);
    }

    onChangeBlur(ev) {
        this.store.settings.setUseBlur(ev.target.checked);
    }

    onChangeShowOnlyVideo(ev) {
        const showOnlyVideo = ev.target.checked;
        this.store.settings.showOnlyVideo = showOnlyVideo;
        browser.localStorage.setItem(
            "mail_user_setting_show_only_video",
            this.store.settings.showOnlyVideo
        );
        const activeRtcSessions = this.store.allActiveRtcSessions;
        if (showOnlyVideo && activeRtcSessions) {
            activeRtcSessions
                .filter((rtcSession) => !rtcSession.videoStream)
                .forEach((rtcSession) => {
                    rtcSession.channel.activeRtcSession = undefined;
                });
        }
    }

    onChangeBackgroundBlurAmount(ev) {
        this.store.settings.backgroundBlurAmount = Number(ev.target.value);
        this.saveBackgroundBlurAmount();
    }

    onChangeEdgeBlurAmount(ev) {
        this.store.settings.edgeBlurAmount = Number(ev.target.value);
        this.saveEdgeBlurAmount();
    }
}

export class CallSettingsDialog extends Component {
    static template = xml`
        <Dialog size="medium" footer="false" title.translate="Voice &amp; Video Settings">
            <CallSettings withActionPanel="false"/>
        </Dialog>
    `;
    static props = ["*"];
    static components = { CallSettings, Dialog };
}
