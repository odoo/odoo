import { useRef } from "@web/owl2/utils";
import { Component, onMounted, onPatched, props, status, types, useListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CallParticipantVideo extends Component {
    static template = "discuss.CallParticipantVideo";

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.props = props({
            "inset?": types.function([
                types.instanceOf(this.store["discuss.channel.rtc.session"].Class),
                types.selection(["camera", "screen"]),
            ]),
            session: types.instanceOf(this.store["discuss.channel.rtc.session"].Class),
            type: types.selection(["camera", "screen"]),
        });
        this.root = useRef("root");
        onMounted(() => this._update());
        onPatched(() => this._update());
        useListener(this.env.bus, "RTC-SERVICE:PLAY_MEDIA", async () => {
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
