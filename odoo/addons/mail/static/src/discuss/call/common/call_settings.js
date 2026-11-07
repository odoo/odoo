/* @odoo-module */

import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

export class CallSettings extends Component {
    static components = { ActionPanel };
    static template = "discuss.CallSettings";
    static props = ["thread", "className?"];

    setup() {
        this.notification = useService("notification");
        this.userSettings = useState(useService("mail.user_settings"));
        this.rtc = useState(useService("discuss.rtc"));
        this.state = useState({
            userDevices: [],
        });
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
        const { shiftKey, ctrlKey, altKey, key } = this.userSettings.pushToTalkKeyFormat();
        const f = (k, name) => (k ? name : "");
        const keys = [f(ctrlKey, "Ctrl"), f(altKey, "Alt"), f(shiftKey, "Shift"), key].filter(
            Boolean
        );
        return keys.join(" + ");
    }

    _onKeyDown(ev) {
        if (!this.userSettings.isRegisteringKey) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.userSettings.setPushToTalkKey(ev);
    }

    _onKeyUp(ev) {
        if (!this.userSettings.isRegisteringKey) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.userSettings.isRegisteringKey = false;
    }

    onChangeLogRtcCheckbox(ev) {
        this.userSettings.logRtc = ev.target.checked;
    }

    onChangeSelectAudioInput(ev) {
        this.userSettings.setAudioInputDevice(ev.target.value);
    }

    onChangePushToTalk() {
        if (this.userSettings.usePushToTalk) {
            this.userSettings.isRegisteringKey = false;
        }
        this.userSettings.togglePushToTalk();
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
        this.userSettings.isRegisteringKey = !this.userSettings.isRegisteringKey;
    }

    onChangeDelay(ev) {
        this.userSettings.setDelayValue(ev.target.value);
    }

    onChangeThreshold(ev) {
        this.userSettings.setThresholdValue(parseFloat(ev.target.value));
    }

    onChangeBlur(ev) {
        this.userSettings.useBlur = ev.target.checked;
    }

    onChangeVideoFilterCheckbox(ev) {
        const showOnlyVideo = ev.target.checked;
        this.props.thread.showOnlyVideo = showOnlyVideo;
        const activeRtcSession = this.props.thread.activeRtcSession;
        if (showOnlyVideo && activeRtcSession && !activeRtcSession.videoStream) {
            this.props.thread.activeRtcSession = undefined;
        }
    }

    onChangeBackgroundBlurAmount(ev) {
        this.userSettings.backgroundBlurAmount = Number(ev.target.value);
    }

    onChangeEdgeBlurAmount(ev) {
        this.userSettings.edgeBlurAmount = Number(ev.target.value);
    }

    get title() {
        return _t("Voice Settings");
    }
}
