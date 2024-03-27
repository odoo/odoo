import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

export class DiscussCallSettings extends Component {
    static props = ["*"];
    static template = "discuss.DiscussCallSettings";

    setup() {
        this.notification = useService("notification");
        this.rtc = useState(useService("discuss.rtc"));
        this.store = useState(useService("mail.store"));
        this.state = useState({
            devices: [],
        });
        this.pttExtService = useState(useService("discuss.ptt_extension"));
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
            this.state.devices = await browser.navigator.mediaDevices.enumerateDevices();
        });
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

    get pushToTalkKeyText() {
        const { shiftKey, ctrlKey, altKey, key } = this.store.settings.pushToTalkKeyFormat();
        const f = (k, name) => (k ? name : "");
        const keys = [f(ctrlKey, "Ctrl"), f(altKey, "Alt"), f(shiftKey, "Shift"), key].filter(
            Boolean
        );
        return keys.join(" + ");
    }

    onClickRegisterKey() {
        this.store.settings.isRegisteringKey = !this.store.settings.isRegisteringKey;
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

    onChangeLogRtc(ev) {
        this.store.settings.logRtc = ev.target.checked;
    }

    onChangeInputDevice(ev) {
        this.store.settings.setAudioInputDevice(ev.target.value);
    }

    onChangeDelay(ev) {
        this.store.settings.setDelayValue(ev.target.value);
    }

    onChangeThreshold(ev) {
        this.store.settings.setThresholdValue(parseFloat(ev.target.value));
    }

    onChangeShowOnlyVideo(ev) {
        this.store.settings.showOnlyVideo = ev.target.checked;
    }

    onChangeBackgroundBlurAmount(ev) {
        this.store.settings.backgroundBlurAmount = Number(ev.target.value);
    }

    onChangeEdgeBlurAmount(ev) {
        this.store.settings.edgeBlurAmount = Number(ev.target.value);
    }
}
