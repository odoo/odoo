import {
    Component,
    onWillUnmount,
    signal,
    status,
    t,
    useEffect,
    useListener,
    useProps,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CallParticipantVideo extends Component {
    static template = "discuss.CallParticipantVideo";

    root = signal.ref();

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.props = useProps({
            inset: t
                .function([
                    t.instanceOf(this.store["discuss.channel.rtc.session"].Class),
                    t.selection(["camera", "screen"]),
                ])
                .optional(),
            session: t.instanceOf(this.store["discuss.channel.rtc.session"].Class),
            type: t.selection(["camera", "screen"]),
            videoStream: t.instanceOf(MediaStream),
        });
        useEffect(() => {
            const stream = this.props.videoStream;
            const video = this.root();
            if (!video || video.srcObject === stream) {
                return;
            }
            video.srcObject = stream;
            video.load();
        });
        onWillUnmount(() => {
            if (this.root()) {
                // A <video>/<audio> element with an active srcObject is kept alive by the
                // browser even after being detached from the DOM, which retains this
                // component (and everything it references) through the loadedmetadata
                // listener. Clearing srcObject releases it for garbage collection.
                this.root().srcObject = null;
                this.root().load();
            }
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
