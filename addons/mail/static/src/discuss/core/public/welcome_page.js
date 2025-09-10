import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { DeviceSelect } from "@mail/discuss/call/common/device_select";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { CallPermissionDialog } from "@mail/discuss/call/common/call_permission_dialog";

export class WelcomePage extends Component {
    static props = ["proceed?"];
    static template = "mail.WelcomePage";
    static components = { DeviceSelect };

    /** @type {BlurManager} */
    blurManager;

    setup() {
        super.setup();
        this.isClosed = false;
        this.dialog = useService("dialog");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.rtc = useService("discuss.rtc");
        this.state = useState({
            userName: this.store.self.name || _t("Guest"),
            audioStream: null,
            videoStream: null,
        });
        this.audioRef = useRef("audio");
        this.videoRef = useRef("video");
        useEffect(
            () => {
                if (this.state.audioStream) {
                    this.stopTracksOnMediaStream(this.state.audioStream);
                    this.enableMicrophone();
                }
            },
            () => [this.store.settings.audioInputDeviceId]
        );
        useEffect(
            () => {
                if (this.state.videoStream) {
                    this.stopTracksOnMediaStream(this.state.videoStream);
                    this.enableVideo();
                }
            },
            () => [this.store.settings.cameraInputDeviceId]
        );
        useEffect(
            (deviceId) => {
                this.audioRef.el?.setSinkId?.(deviceId).catch(() => {});
            },
            () => [this.store.settings.audioOutputDeviceId]
        );
    }

    onKeydownInput(ev) {
        if (ev.key === "Enter") {
            this.joinChannel();
        }
    }

    joinChannel() {
        if (!this.store.self_partner) {
            this.store.self_guest?.updateGuestName(this.state.userName.trim());
        }
        browser.localStorage.setItem("discuss_call_preview_join_mute", !this.state.audioStream);
        browser.localStorage.setItem(
            "discuss_call_preview_join_video",
            Boolean(this.state.videoStream)
        );
        this.stopTracksOnMediaStream(this.state.audioStream);
        this.stopTracksOnMediaStream(this.state.videoStream);
        this.blurManager?.close();
        this.blurManager = undefined;
        this.isClosed = true;
        this.props.proceed?.();
    }

    get hasRtcSupport() {
        return Boolean(
            navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaStream
        );
    }

    get blurButtonTitle() {
        return this.store.settings.useBlur ? _t("Remove Blur Background") : _t("Blur Background");
    }

    async enableMicrophone() {
        if (!this.hasRtcSupport || !(await this.rtc.askForBrowserPermission({ audio: true }))) {
            return;
        }
        this.state.audioStream = await navigator.mediaDevices.getUserMedia({
            audio: this.store.settings.audioConstraints,
        });
        this.audioRef.el.srcObject = this.state.audioStream;
        if (this.isClosed) {
            this.stopTracksOnMediaStream(this.state.audioStream);
        }
    }

    disableMicrophone() {
        this.audioRef.el.srcObject = null;
        this.stopTracksOnMediaStream(this.state.audioStream);
        this.state.audioStream = null;
    }

    async enableVideo() {
        if (!this.hasRtcSupport || !(await this.rtc.askForBrowserPermission({ video: true }))) {
            return;
        }
        this.state.videoStream = await navigator.mediaDevices.getUserMedia({
            video: this.store.settings.cameraConstraints,
        });
        await this.applyBlurConditionally();
        if (this.isClosed) {
            this.stopTracksOnMediaStream(this.state.videoStream);
        }
    }

    async onClickBlur() {
        this.store.settings.useBlur = !this.store.settings.useBlur;
        await this.applyBlurConditionally();
    }

    async applyBlurConditionally() {
        if (!this.state.videoStream) {
            return;
        }
        if (!this.store.settings.useBlur) {
            this.videoRef.el.srcObject = this.state.videoStream;
            return;
        }
        this.blurManager?.close();
        this.blurManager = undefined;
        try {
            this.blurManager = await this.rtc.applyBlurEffect(this.state.videoStream);
            this.videoRef.el.srcObject = this.blurManager.stream;
        } catch (_e) {
            this.notification.add(_e.message, { type: "warning" });
            this.store.settings.useBlur = false;
            this.videoRef.el.srcObject = this.state.videoStream;
        }
    }

    disableVideo() {
        this.videoRef.el.srcObject = null;
        this.stopTracksOnMediaStream(this.state.videoStream);
        this.state.videoStream = null;
        this.blurManager?.close();
        this.blurManager = undefined;
    }

    /**
     * @param {MediaStream} mediaStream
     */
    stopTracksOnMediaStream(mediaStream) {
        if (!mediaStream) {
            return;
        }
        for (const track of mediaStream.getTracks()) {
            track.stop();
        }
    }

    async onClickMic() {
        if (this.state.audioStream) {
            this.disableMicrophone();
            return;
        }
        if (this.rtc.microphonePermission === "prompt") {
            this.dialog.add(CallPermissionDialog, {
                media: "microphone",
                useMicrophone: () => this.enableMicrophone(),
                useCamera: () => this.enableVideo(),
            });
            return;
        }
        await this.enableMicrophone();
    }

    async onClickVideo() {
        if (this.state.videoStream) {
            this.disableVideo();
            return;
        }
        if (this.rtc.cameraPermission === "prompt") {
            this.dialog.add(CallPermissionDialog, {
                media: "camera",
                useMicrophone: () => this.enableMicrophone(),
                useCamera: () => this.enableVideo(),
            });
            return;
        }
        await this.enableVideo();
    }

    getLoggedInAsText() {
        return _t("Logged in as %s", this.store.self.name);
    }

    get noActiveParticipants() {
        return !this.store.discuss.thread.rtc_session_ids.length;
    }
}
