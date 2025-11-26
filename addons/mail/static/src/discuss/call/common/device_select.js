import { Component, onWillDestroy, onWillStart, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { isBrowserChrome } from "@web/core/browser/feature_detection";

const deviceKind = new Set(["audioinput", "videoinput", "audiooutput"]);

export class DeviceSelect extends Component {
    static props = {
        kind: {
            type: String,
            validate: (string) => deviceKind.has(string),
        },
        icon: {
            type: String,
            optional: true,
        },
        roundedType: {
            type: String,
            optional: true,
        },
    };
    static components = { Dropdown, DropdownItem };
    static template = "discuss.CallDeviceSelect";
    PERMISSION_NEEDED = _t("Permission Needed");
    BROWSER_DEFAULT = isBrowserChrome() ? _t("Default") : _t("Browser Default");

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.notification = useService("notification");
        this.state = useState({
            userDevices: [],
            selectedDevice: undefined,
            isSelectOpen: false,
        });
        this.abortController = new AbortController();
        this.isBrowserChrome = isBrowserChrome();
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
            this.state.selectedDevice = this.state.userDevices.find((device) =>
                this.isSelected(device.deviceId)
            );
            this.setupEventListeners();
        });
        onWillDestroy(() => {
            this.abortController.abort();
        });
    }

    get selectLabel() {
        return this.state.selectedDevice?.label;
    }

    openSelect(state) {
        if (state === true) {
            this.state.isSelectOpen = true;
        } else if (state === false) {
            this.state.isSelectOpen = false;
        }
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

    async showPermissionDialog(kind) {
        if (kind === "videoinput") {
            if (this.store.rtc.cameraPermission === "denied") {
                this.store.rtc.showMediaUnavailableWarning({ camera: true });
            } else {
                this.store.rtc.showMediaPermissionDialog("camera");
                return;
            }
        } else {
            if (this.store.rtc.microphonePermission === "denied") {
                this.store.rtc.showMediaUnavailableWarning({ microphone: true });
            } else {
                this.store.rtc.showMediaPermissionDialog("microphone");
                return;
            }
        }
    }

    isSelected(id) {
        if (id === undefined) {
            id = "";
        }
        switch (this.props.kind) {
            case "audioinput":
                return (
                    this.store.settings.audioInputDeviceId === id ||
                    (this.isBrowserChrome &&
                        this.store.settings.audioInputDeviceId === "" &&
                        id === "default")
                );
            case "videoinput":
                return this.store.settings.cameraInputDeviceId === id;
            case "audiooutput":
                return (
                    this.store.settings.audioOutputDeviceId === id ||
                    (this.isBrowserChrome &&
                        this.store.settings.audioOutputDeviceId === "" &&
                        id === "default")
                );
        }
    }

    onSelectAudioDevice(device) {
        this.state.selectedDevice = device;
        const deviceId = device?.deviceId ?? "";
        switch (this.props.kind) {
            case "audioinput":
                this.store.settings.audioInputDeviceId = deviceId;
                return;
            case "videoinput":
                this.store.settings.cameraInputDeviceId = deviceId;
                return;
            case "audiooutput":
                this.store.settings.audioOutputDeviceId = deviceId;
                return;
        }
    }

    isPermissionGranted(kind) {
        if (kind === "videoinput") {
            return this.store.rtc.cameraPermission === "granted";
        }
        return this.store.rtc.microphonePermission === "granted";
    }
}
