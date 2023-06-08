/* @odoo-module */

import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { Component, onMounted, onPatched, useExternalListener, useRef } from "@odoo/owl";

export class CallParticipantVideo extends Component {
    static props = ["session"];
    static template = "discuss.CallParticipantVideo";

    setup() {
        this.rtc = useRtc();
        this.root = useRef("root");
        onMounted(() => this._update());
        onPatched(() => this._update());
        useExternalListener(this.env.bus, "RTC-SERVICE:PLAY_MEDIA", async () => {
            await this.play();
        });
    }

    _update() {
        if (!this.root.el) {
            return;
        }
        if (!this.props.session || !this.props.session.videoStream) {
            this.root.el.srcObject = undefined;
        } else {
            this.root.el.srcObject = this.props.session.videoStream;
        }
        this.root.el.load();
    }

    async play() {
        try {
            await this.root.el?.play?.();
            this.props.session.videoError = undefined;
        } catch (error) {
            this.props.session.videoError = error.name;
        }
    }

    async onVideoLoadedMetaData() {
        await this.play();
    }
}
