import { Component, onWillStart, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

const deviceKind = new Set(["audioinput", "videoinput", "audiooutput"]);

export class DeviceSelect extends Component {
    static props = {
        kind: {
            type: String,
            validate: (string) => deviceKind.has(string),
        },
    };
    static template = "discuss.CallDeviceSelect";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.state = useState({
            userDevices: [],
        });
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

    isSelected(id) {
        switch (this.props.kind) {
            case "audioinput":
                return this.store.settings.audioInputDeviceId === id;
            case "videoinput":
                return this.store.settings.cameraInputDeviceId === id;
            case "audiooutput":
                return this.store.settings.audioOutputDeviceId === id;
        }
    }

    onChangeSelectAudioInput(ev) {
        switch (this.props.kind) {
            case "audioinput":
                this.store.settings.setAudioInputDevice(ev.target.value);
                return;
            case "videoinput":
                this.store.settings.setCameraInputDevice(ev.target.value);
                return;
            case "audiooutput":
                this.store.settings.setAudioOutputDevice(ev.target.value);
                return;
        }
    }
}
