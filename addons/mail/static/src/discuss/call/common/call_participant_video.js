import { Component, props, signal, status, t, useEffect, useListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CallParticipantVideo extends Component {
    static template = "discuss.CallParticipantVideo";

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.props = props({
            inset: t
                .function([
                    t.instanceOf(this.store["discuss.channel.rtc.session"].Class),
                    t.selection(["camera", "screen"]),
                ])
                .optional(),
            session: t.instanceOf(this.store["discuss.channel.rtc.session"].Class),
            type: t.selection(["camera", "screen"]),
        });
        this.root = signal.ref();
        useEffect(() => {
            const el = this.root();
            if (!el) {
                return;
            }
            el.srcObject = this.props.session.getStream(this.props.type) || null;
            el.load();
            return () => {
                el.srcObject = null;
                el.load();
            };
        });
        useListener(this.env.bus, "RTC-SERVICE:PLAY_MEDIA", async () => {
            await this.play();
        });
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
