import { Component, onWillDestroy, onWillStart, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
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
        this.notification = useService("notification");
        this.state = useState({
            userDevices: [],
        });
        this.abortController = new AbortController();
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
            await this.updateDevicesList();
            this.setupEventListeners();
        });
        onWillDestroy(() => {
            this.abortController.abort();
        });
    }

    async updateDevicesList() {
        this.state.userDevices = await browser.navigator.mediaDevices.enumerateDevices();
    }

    async setupEventListeners() {
        const boundHandler = this.updateDevicesList.bind(this);
        const signal = this.abortController.signal;

        browser.navigator.mediaDevices.addEventListener("devicechange", boundHandler, { signal });
        if (this.props.kind == "videoinput") {
            const cameraPermission = await browser.navigator.permissions.query({ name: "camera" });
            cameraPermission.addEventListener("change", boundHandler, { signal });
        } else {
            const microphonePermission = await browser.navigator.permissions.query({
                name: "microphone",
            });
            microphonePermission.addEventListener("change", boundHandler, { signal });
        }
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
