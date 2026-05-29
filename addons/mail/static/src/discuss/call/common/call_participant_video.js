import { useExternalListener } from "@web/owl2/utils";
import { Component, onMounted, onPatched, signal, status } from "@odoo/owl";
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
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.root = signal();
        onMounted(() => this._update());
        onPatched(() => this._update());
        useExternalListener(this.env.bus, "RTC-SERVICE:PLAY_MEDIA", async () => {
            await this.play();
        });
    }

    _update() {
        if (!this.root()) {
            return;
        }
        if (!this.props.session || !this.props.session.getStream(this.props.type)) {
            this.root().srcObject = undefined;
        } else {
            this.root().srcObject = this.props.session.getStream(this.props.type);
        }
        this.root().load();
    }

    async play() {
        try {
            await this.root()?.play?.();
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
