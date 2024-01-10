/* @odoo-module */

import { Component, useRef, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

export class WelcomePage extends Component {
    static props = ["data?", "proceed?"];
    static template = "mail.WelcomePage";

    setup() {
        this.store = useState(useService("mail.store"));
        this.rpc = useService("rpc");
        this.personaService = useService("mail.persona");
        this.state = useState({
            userName: "Guest",
            audioStream: null,
            videoStream: null,
        });
        this.audioRef = useRef("audio");
        this.videoRef = useRef("video");
    }

    onKeydownInput(ev) {
        if (ev.key === "Enter") {
            this.joinChannel();
        }
    }

    async joinChannel() {
        if (this.store.guest) {
            await this.personaService.updateGuestName(this.store.self, this.state.userName.trim());
        }
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
            this.audioRef.el.srcObject = this.audioStream;
        } catch {
            // TODO: display popup asking the user to re-enable their mic
        }
    }

    disableMicrophone() {
        this.audioRef.el.srcObject = null;
        if (!this.state.audioStream) {
            return;
        }
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
    }

    disableVideo() {
        this.videoRef.el.srcObject = null;
        if (!this.state.videoStream) {
            return;
        }
        this.stopTracksOnMediaStream(this.state.videoStream);
        this.state.videoStream = null;
    }

    /**
     * @param {MediaStream} mediaStream
     */
    stopTracksOnMediaStream(mediaStream) {
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
        browser.localStorage.setItem(
            "discuss_call_preview_join_mute",
            Boolean(!this.state.audioStream)
        );
    }

    async onClickVideo() {
        if (!this.state.videoStream) {
            await this.enableVideo();
        } else {
            this.disableVideo();
        }
        browser.localStorage.setItem(
            "discuss_call_preview_join_video",
            Boolean(this.state.videoStream)
        );
    }
    getLoggedInAsText() {
        return sprintf(_t("Logged in as %s"), this.store.user.name);
    }
}
