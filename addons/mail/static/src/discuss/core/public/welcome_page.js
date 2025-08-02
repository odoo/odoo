import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";

import { DeviceSelect } from "@mail/discuss/call/common/device_select";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class WelcomePage extends Component {
    static props = ["proceed?"];
    static template = "mail.WelcomePage";
    static components = { DeviceSelect };

    setup() {
        super.setup();
        this.isClosed = false;
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.state = useState({
            userName: this.store.self.name || _t("Guest"),
            audioStream: null,
            videoStream: null,
        });
        this.audioRef = useRef("audio");
        this.videoRef = useRef("video");
        onMounted(() => {
            if (this.store.discuss_public_thread.default_display_mode === "video_full_screen") {
                this.enableMicrophone();
                this.enableVideo();
            }
        });
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
        this.isClosed = true;
        this.props.proceed?.();
    }

    get hasRtcSupport() {
        return Boolean(
            navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaStream
        );
    }

    async enableMicrophone() {
        if (!this.hasRtcSupport) {
            return;
        }
        try {
            this.state.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: this.store.settings.audioConstraints,
            });
            this.audioRef.el.srcObject = this.state.audioStream;
        } catch {
            // TODO: display popup asking the user to re-enable their mic
        }
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
        if (!this.hasRtcSupport) {
            return;
        }
        try {
            this.state.videoStream = await navigator.mediaDevices.getUserMedia({
                video: this.store.settings.cameraConstraints,
            });
            this.videoRef.el.srcObject = this.state.videoStream;
        } catch {
            // TODO: display popup asking the user to re-enable their camera
        }
        if (this.isClosed) {
            this.stopTracksOnMediaStream(this.state.videoStream);
        }
    }

    disableVideo() {
        this.videoRef.el.srcObject = null;
        this.stopTracksOnMediaStream(this.state.videoStream);
        this.state.videoStream = null;
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
        if (!this.state.audioStream) {
            await this.enableMicrophone();
        } else {
            this.disableMicrophone();
        }
    }

    async onClickVideo() {
        if (!this.state.videoStream) {
            await this.enableVideo();
        } else {
            this.disableVideo();
        }
    }
    getLoggedInAsText() {
        return _t("Logged in as %s", this.store.self.name);
    }
}
