/* @odoo-module */

import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";

export class CallSettings extends Component {
    static template = "mail.call_settings";
    static props = ["thread", "className?"];

    setup() {
        this.userSettings = useState(useService("mail.user_settings"));
        this.rtc = useRtc();
        this.state = useState({
            userDevices: [],
        });
        useExternalListener(browser, "keydown", this._onKeyDown);
        useExternalListener(browser, "keyup", this._onKeyUp);
        onWillStart(async () => {
            this.state.userDevices = await browser.navigator.mediaDevices.enumerateDevices();
        });
    }

    get pushToTalkKeyText() {
        const { shiftKey, ctrlKey, altKey, key } = this.userSettings.pushToTalkKeyFormat();
        const f = (k, name) => (k ? name : "");
        return `${f(ctrlKey, "Ctrl + ")}${f(altKey, "Alt + ")}${f(shiftKey, "Shift + ")}${key}`;
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
        const data = window.JSON.stringify(Object.fromEntries(this.rtc.state.logs));
        const blob = new window.Blob([data], { type: "application/json" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `RtcLogs_Channel_${this.rtc.state.logs.channelId}_Session_${
            this.rtc.state.logs.selfSessionId
        }_${window.moment().format("YYYY-MM-DD_HH-mm")}.json`;
        a.click();
        window.URL.revokeObjectURL(url);
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

    onChangeVideoFilterCheckbox(ev) {
        const showOnlyVideo = ev.target.checked;
        this.props.thread.showOnlyVideo = showOnlyVideo;
        const activeRtcSession = this.props.thread.activeRtcSession;
        if (showOnlyVideo && activeRtcSession && !activeRtcSession.videoStream) {
            this.props.thread.activeRtcSession = undefined;
        }
    }

    onChangeBlur(ev) {
        this.userSettings.useBlur = !this.userSettings.useBlur;
    }

    onChangeBackgroundBlurAmount(ev) {
        this.userSettings.backgroundBlurAmount = Number(ev.target.value);
    }

    onChangeEdgeBlurAmount(ev) {
        this.userSettings.edgeBlurAmount = Number(ev.target.value);
    }
}
