import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

export class CallSettings extends Component {
    static template = "discuss.CallSettings";
    static props = ["withActionPanel?", "*"];
    static defaultProps = {
        withActionPanel: true,
    };
    static components = { ActionPanel };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.store = useState(useService("mail.store"));
        this.rtc = useState(useService("discuss.rtc"));
        this.state = useState({
            userDevices: [],
        });
        this.pttExtService = useState(useService("discuss.ptt_extension"));
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
        const data = JSON.stringify(Object.fromEntries(this.rtc.state.logs));
        const blob = new Blob([data], { type: "application/json" });
        const downloadLink = document.createElement("a");
        const channelId = this.rtc.state.logs.get("channelId");
        const sessionId = this.rtc.state.logs.get("selfSessionId");
        const now = luxon.DateTime.now().toFormat("yyyy-ll-dd_HH-mm");
        downloadLink.download = `RtcLogs_Channel_${channelId}_Session_${sessionId}_${now}.json`;
        const url = URL.createObjectURL(blob);
        downloadLink.href = url;
        downloadLink.click();
        URL.revokeObjectURL(url);
    }

    onClickRegisterKeyButton() {
        this.store.settings.isRegisteringKey = !this.store.settings.isRegisteringKey;
    }

    onChangeDelay(ev) {
        this.store.settings.setDelayValue(ev.target.value);
    }

    onChangeThreshold(ev) {
        this.store.settings.setThresholdValue(parseFloat(ev.target.value));
    }

    onChangeBlur(ev) {
        this.store.settings.useBlur = ev.target.checked;
        browser.localStorage.setItem("mail_user_setting_use_blur", this.store.settings.useBlur);
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
