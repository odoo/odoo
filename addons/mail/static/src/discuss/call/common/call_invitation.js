import { Component, onWillUnmount, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CallInvitation extends Component {
    static props = ["thread"];
    static template = "discuss.CallInvitation";

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.ui = useService("ui");
        this.state = useState({ videoStream: null });
        this.videoRef = useRef("video");
        onWillUnmount(() => {
            if (!this.state.videoStream) {
                return;
            }
            this.stopTracksOnMediaStream(this.state.videoStream);
        });
    }

    async onClickAccept(ev, { camera = false } = {}) {
        this.props.thread.open();
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        await this.rtc.toggleCall(this.props.thread, { camera });
    }

    onClickAvatar(ev) {
        this.props.thread.open();
    }

    get hasRtcSupport() {
        return Boolean(
            navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaStream
        );
    }

    onClickPreviewCamera() {
        this.enableVideo();
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

    /** @param {MediaStream} mediaStream */
    stopTracksOnMediaStream(mediaStream) {
        if (!mediaStream) {
            return;
        }
        for (const track of mediaStream.getTracks()) {
            track.stop();
        }
    }

    onClickRefuse(ev) {
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        this.rtc.leaveCall(this.props.thread);
    }
}
