import { Action, ACTION_TAGS } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import {
    cameraOnAction,
    muteAction,
    quickActionSettings,
    quickVideoSettings,
} from "@mail/discuss/call/common/call_actions";
import { CallPermissionDialog } from "@mail/discuss/call/common/call_permission_dialog";
import { CallSettingsDialog } from "@mail/discuss/call/common/call_settings";
import { DeviceSelect } from "@mail/discuss/call/common/device_select";
import { closeStream, onChange } from "@mail/utils/common/misc";

import { Component, onWillDestroy, status, useEffect, useRef, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {Number} [activateCamera]
 * @property {Number} [activateMicrophone]
 * @property {({ microphone?: boolean, camera?: boolean }) => void} [onSettingsChanged]
 * @extends {Component<Props, Env>}
 */
export class CallPreview extends Component {
    static template = "mail.CallPreview";
    static props = [
        "activateCamera?",
        "activateMicrophone?",
        "onSettingsChanged?",
        "hasSettingsAtBottom?",
    ];
    static components = { ActionList, DeviceSelect };

    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.state = useState({ audioStream: null, blurManager: null, videoStream: null });
        this.audioRef = useRef("audio");
        this.videoRef = useRef("video");
        useEffect(
            (videoEl, audioEl, audioStream, videoStream, blurStream) => {
                if (audioEl && !audioEl.srcObject && audioStream) {
                    audioEl.srcObject = audioStream;
                }
                if (videoEl && !videoEl.srcObject && videoStream) {
                    videoEl.srcObject = blurStream ?? videoStream;
                }
            },
            () => [
                this.videoRef.el,
                this.audioRef.el,
                this.state.audioStream,
                this.state.videoStream,
                this.state.blurManager?.stream,
            ]
        );
        if (this.hasRtcSupport) {
            onChange(this.rtc, "microphonePermission", () => {
                if (this.rtc.microphonePermission !== "granted") {
                    this.disableMicrophone();
                }
            });
            onChange(this.rtc, "cameraPermission", () => {
                if (this.rtc.cameraPermission !== "granted") {
                    this.disableCamera();
                }
            });
            onChange(this.store.settings, "audioInputDeviceId", () => {
                if (this.state.audioStream) {
                    closeStream(this.state.audioStream);
                    this.enableMicrophone();
                }
            });
            onChange(this.store.settings, "cameraInputDeviceId", () => {
                if (this.state.videoStream) {
                    closeStream(this.state.videoStream);
                    this.enableCamera();
                }
            });
            onChange(this.store.settings, "audioOutputDeviceId", (deviceId) => {
                this.audioRef.el?.setSinkId?.(deviceId).catch(() => {});
            });
            onChange(this.store.settings, "useBlur", () => {
                if (this.store.settings.useBlur) {
                    this.enableBlur();
                } else {
                    this.disableBlur();
                }
            });
            onChange(this.store.settings, ["edgeBlurAmount", "backgroundBlurAmount"], () => {
                if (this.state.blurManager) {
                    this.state.blurManager.edgeBlur = this.store.settings.edgeBlurAmount;
                    this.state.blurManager.backgroundBlur =
                        this.store.settings.backgroundBlurAmount;
                }
            });
            onWillDestroy(() => {
                closeStream(this.state.audioStream);
                closeStream(this.state.videoStream);
            });
            useEffect(
                (activateCamera) => {
                    if (activateCamera > 0 && !this.state.videoStream) {
                        this.enableCamera();
                    }
                },
                () => [this.props.activateCamera]
            );
            useEffect(
                (activateMicrophone) => {
                    if (activateMicrophone > 0 && !this.state.audioStream) {
                        this.enableMicrophone();
                    }
                },
                () => [this.props.activateMicrophone]
            );
        }
    }

    get hasRtcSupport() {
        return Boolean(
            navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaStream
        );
    }

    get actions() {
        const cameraOnActionUpdated = {
            ...cameraOnAction,
            isActive: () => this.state.videoStream,
            name: ({ action }) => (action.isActive ? _t("Stop camera") : _t("Turn camera on")),
            onSelected: () => this.toggleCamera(),
            tags: (...args) => {
                const tags = cameraOnAction.tags?.(...args) ?? [];
                if (!args[0].action.isActive && this.rtc.cameraPermission !== "granted") {
                    tags.push(ACTION_TAGS.DANGER);
                }
                return tags;
            },
        };
        const muteActionUpdated = {
            ...muteAction,
            isActive: () => !this.state.audioStream,
            name: ({ action }) => (action.isActive ? _t("Unmute") : _t("Mute")),
            onSelected: () => this.toggleMic(),
        };
        const videoBlurAction = {
            condition: () => this.state.videoStream !== null,
            icon: () => "fa fa-fw fa-photo",
            isActive: ({ store }) => store.settings.useBlur,
            name: ({ action }) =>
                action.isActive ? _t("Disable background blur") : _t("Enable background blur"),
            onSelected: ({ store }) => {
                store.settings.useBlur = !store.settings.useBlur;
            },
            tags: ({ action }) => (action.isActive ? [ACTION_TAGS.SUCCESS] : []),
        };
        const callAudioActions = [
            new Action({
                id: "toggle-microphone",
                owner: this,
                definition: muteActionUpdated,
                store: this.store,
            }),
        ];
        const callVideoActions = [
            new Action({
                id: "toggle-camera",
                owner: this,
                definition: cameraOnActionUpdated,
                store: this.store,
            }),
        ];
        if (this.props.hasSettingsAtBottom) {
            callVideoActions.push(
                new Action({
                    id: "video-blur",
                    owner: this,
                    definition: videoBlurAction,
                    store: this.store,
                })
            );
        } else {
            callAudioActions.push(
                new Action({
                    id: "audio-settings",
                    owner: this,
                    definition: quickActionSettings,
                    store: this.store,
                })
            );
            callVideoActions.push(
                new Action({
                    id: "video-settings",
                    owner: this,
                    definition: quickVideoSettings,
                    store: this.store,
                })
            );
        }

        return [callAudioActions, callVideoActions];
    }

    async enableMicrophone() {
        if (
            this.rtc.microphonePermission !== "granted" &&
            !(await this.rtc.askForBrowserPermission({ audio: true }))
        ) {
            return;
        }
        this.state.audioStream = await navigator.mediaDevices.getUserMedia({
            audio: this.store.settings.audioConstraints,
        });
        if (status(this) === "destroyed") {
            closeStream(this.state.audioStream);
            return;
        }
        if (this.audioRef.el) {
            this.audioRef.el.srcObject = this.state.audioStream;
        }
        this.props.onSettingsChanged?.({ microphone: true });
    }

    disableMicrophone() {
        closeStream(this.state.audioStream);
        this.state.audioStream = null;
        if (this.audioRef.el) {
            this.audioRef.el.srcObject = null;
        }
        this.props.onSettingsChanged?.({ microphone: false });
    }

    async toggleMic() {
        if (this.state.audioStream) {
            this.disableMicrophone();
            return;
        }
        if (this.rtc.microphonePermission === "prompt") {
            this.dialog.add(CallPermissionDialog, {
                media: "microphone",
                useMicrophone: () => this.enableMicrophone(),
                useCamera: () => this.enableCamera(),
            });
            return;
        }
        await this.enableMicrophone();
    }

    async enableCamera() {
        if (
            this.rtc.cameraPermission !== "granted" &&
            !(await this.rtc.askForBrowserPermission({ video: true }))
        ) {
            return;
        }
        this.state.videoStream = await navigator.mediaDevices.getUserMedia({
            video: this.store.settings.cameraConstraints,
        });
        if (!this.videoRef.el) {
            return;
        }
        if (status(this) === "destroyed") {
            closeStream(this.state.videoStream);
            return;
        }
        if (this.videoRef.el) {
            this.videoRef.el.srcObject = this.state.videoStream;
        }
        this.props.onSettingsChanged?.({ camera: true });
        if (this.store.settings.useBlur) {
            await this.enableBlur();
        }
    }

    disableCamera() {
        closeStream(this.state.videoStream);
        this.state.videoStream = null;
        this.state.blurManager?.close();
        this.state.blurManager = undefined;
        if (this.videoRef.el) {
            this.videoRef.el.srcObject = null;
        }
        this.props.onSettingsChanged?.({ camera: false });
    }

    async toggleCamera() {
        if (this.state.videoStream) {
            this.disableCamera();
            return;
        }
        if (this.rtc.cameraPermission === "prompt") {
            this.dialog.add(CallPermissionDialog, {
                media: "camera",
                useMicrophone: () => this.enableMicrophone(),
                useCamera: () => this.enableCamera(),
            });
            return;
        }
        await this.enableCamera();
    }

    async enableBlur() {
        this.store.settings.useBlur = true;
        if (!this.videoRef.el) {
            return;
        }
        try {
            this.state.blurManager = await this.rtc.applyBlurEffect(this.state.videoStream);
            this.videoRef.el.srcObject = await this.state.blurManager.stream;
        } catch (_e) {
            this.notification.add(_e.message, { type: "warning" });
            this.disableBlur();
        }
    }

    disableBlur() {
        this.store.settings.useBlur = false;
        if (this.videoRef.el) {
            this.videoRef.el.srcObject = this.state.videoStream;
        }
        this.state.blurManager?.close();
        this.state.blurManager = undefined;
    }

    toggleBlur() {
        if (this.state.blurManager) {
            this.disableBlur();
            return;
        }
        this.enableBlur();
    }

    onClickSettings() {
        this.dialog.add(CallSettingsDialog, {});
    }
}
