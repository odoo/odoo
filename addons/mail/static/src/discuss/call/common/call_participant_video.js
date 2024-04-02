import { Component, onMounted, onPatched, useExternalListener, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").RtcSession} session
 * @extends {Component<Props, Env>}
 */
export class CallParticipantVideo extends Component {
    static props = ["session", "type", "inset?"];
    static template = "discuss.CallParticipantVideo";

    setup() {
        super.setup();
        this.rtc = useState(useService("discuss.rtc"));
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
        if (!this.props.session || !this.props.session.getStream(this.props.type)) {
            this.root.el.srcObject = undefined;
        } else {
            this.root.el.srcObject = this.props.session.getStream(this.props.type);
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
