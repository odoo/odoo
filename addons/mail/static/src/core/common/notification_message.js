import {
    Component,
    onMounted,
    onPatched,
    onWillDestroy,
    onWillUpdateProps,
    useRef,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

export class NotificationMessage extends Component {
    static template = "mail.NotificationMessage";
    static props = ["message", "thread", "registerMessageRef?"];

    setup() {
        super.setup();
        this.root = useRef("root");
        onWillUpdateProps((nextProps) => {
            this.props.registerMessageRef?.(this.props.message, null);
        });
        onMounted(() => this.props.registerMessageRef?.(this.props.message, this.root));
        onPatched(() => this.props.registerMessageRef?.(this.props.message, this.root));
        onWillDestroy(() => this.props.registerMessageRef?.(this.props.message, null));
        this.escape = escape;
        this.store = useService("mail.store");
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickNotificationMessage(ev) {
        this.store.handleClickOnLink(ev, this.props.thread);
        const { oeType, oeId } = ev.target.dataset;
        if (oeType === "highlight") {
            await this.env.messageHighlight?.highlightMessage(
                this.store["mail.message"].insert({
                    id: Number(oeId),
                    res_id: this.props.thread.id,
                    model: this.props.thread.model,
                    thread: this.props.thread,
                }),
                this.props.thread
            );
        }
    }

    get message() {
        return this.props.message;
    }

    get callInformation() {
        if (this.message.create_date.equals(this.message.write_date)) {
            return _t("%(author)s started a call.", { author: this.message.author.name });
        }
        let duration = this.message.write_date.diff(this.message.create_date, [
            "hours",
            "minutes",
            "seconds",
        ]);
        if (duration.hours || duration.minutes) {
            duration = duration.set({ seconds: 0 });
        }
        const units = Object.entries(duration.toObject())
            .filter(([unit, amount]) => amount != 0)
            .map(([unit, amount]) => unit);
        return _t("Call lasted %(duration)s.", {
            duration: duration.shiftTo(...units).toHuman({ unitDisplay: "short" }),
        });
    }
}
