import { Component, signal, t, useEffect, useListener, useProps, useScope } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CallParticipantVideo extends Component {
    static template = "discuss.CallParticipantVideo";

    root = signal.ref();

    scope = useScope();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = this.store.rtc;
        this.props = useProps({
            inset: t.boolean().optional(),
            isCropped: t.boolean().optional(),
            session: t.instanceOf(this.store["discuss.channel.rtc.session"]),
            type: t.selection(["camera", "screen"]),
        });
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
        useListener(this.env.bus, "RTC:PLAY_MEDIA", async () => {
            await this.play();
        });
    }

    async play() {
        try {
            await this.root()?.play?.();
            this.props.session.videoError = undefined;
        } catch (error) {
            if (this.scope.isDestroyed()) {
                return;
            }
            this.props.session.videoError = error.name;
        }
    }

    async onVideoLoadedMetaData() {
        await this.play();
    }
}
