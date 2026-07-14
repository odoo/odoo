import { Component, useRef, useState, onMounted } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

export class WelcomePage extends Component {
    static props = ["proceed?"];
    static template = "mail.WelcomePage";

    setup() {
        super.setup();
        this.isClosed = false;
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.state = useState({
            userName: this.store.self.name || _t("Guest"),
            audioStream: null,
            videoStream: null,
        });
        this.audioRef = useRef("audio");
        this.videoRef = useRef("video");
        onMounted(() => {
            if (this.store.discuss_public_thread.defaultDisplayMode === "video_full_screen") {
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

    async joinChannel() {
        if (this.store.self.type === "guest") {
            await this.store.self.updateGuestName(this.state.userName.trim());
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
        return sprintf(_t("Logged in as %s"), this.store.self.name);
    }
}
