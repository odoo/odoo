import { Component, onMounted, onPatched, signal, status, useListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").RtcSession} session
 * @extends {Component<Props, Env>}
 */
export class CallParticipantVideo extends Component {
    static props = ["session", "type", "inset?"];
    static template = "discuss.CallParticipantVideo";

    rootRef = signal(null);

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        onMounted(() => this._update());
        onPatched(() => this._update());
        useListener(this.env.bus, "RTC-SERVICE:PLAY_MEDIA", async () => {
            await this.play();
        });
    }

    _update() {
        const el = this.rootRef();
        if (!el) {
            return;
        }
        if (!this.props.session || !this.props.session.getStream(this.props.type)) {
            el.srcObject = undefined;
        } else {
            el.srcObject = this.props.session.getStream(this.props.type);
        }
        el.load();
    }

    async play() {
        try {
            await this.rootRef()?.play?.();
            this.props.session.videoError = undefined;
        } catch (error) {
            if (status(this) === "destroyed") {
                return;
            }
            this.props.session.videoError = error.name;
        }
    }

    async onVideoLoadedMetaData() {
        await this.play();
    }
}
