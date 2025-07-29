import { Component, useRef, useState, onMounted } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class WelcomePage extends Component {
    static props = ["proceed?"];
    static template = "mail.WelcomePage";

    /** @type {BlurManager} */
    blurManager;

    setup() {
        super.setup();
        this.isClosed = false;
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
        onMounted(() => {
            if (this.store.discuss_public_thread.default_display_mode === "video_full_screen") {
                this.enableMicrophone();
                this.enableVideo();
            }
        });
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
        if (!this.hasRtcSupport) {
            return;
        }
        try {
            this.state.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
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
            this.state.videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
            await this.applyBlurConditionally();
        } catch {
            // TODO: display popup asking the user to re-enable their camera
        }
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
