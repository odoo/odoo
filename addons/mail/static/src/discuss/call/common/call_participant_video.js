import { useExternalListener, useRef } from "@web/owl2/utils";
import { Component, onMounted, onPatched, onWillUnmount, status } from "@odoo/owl";
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
        this.root = useRef("root");
        onMounted(() => this._update());
        onPatched(() => this._update());
        onWillUnmount(() => {
            if (this.root.el) {
                // A <video>/<audio> element with an active srcObject is kept alive by the
                // browser even after being detached from the DOM, which retains this
                // component (and everything it references) through the loadedmetadata
                // listener. Clearing srcObject releases it for garbage collection.
                this.root.el.srcObject = null;
                this.root.el.load();
            }
        });
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
