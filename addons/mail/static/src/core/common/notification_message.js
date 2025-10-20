import { useForwardRefsToParent } from "@mail/utils/common/hooks";
import { Component, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

export class NotificationMessage extends Component {
    static template = "mail.NotificationMessage";
    static props = ["message", "messageRefs?", "thread"];

    setup() {
        super.setup();
        this.root = useRef("root");
        useForwardRefsToParent("messageRefs", (props) => props.message.id, this.root);
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
        const history = this.message.call_history_ids[0];
        if (history?.duration_hour === undefined || !history?.end_dt) {
            return _t("%(author)s started a call.", { author: this.message.authorName });
        }
        let duration = luxon.Duration.fromObject({
            seconds: Math.max(1, Math.round(history.duration_hour * 3600)),
        }).shiftTo("hours", "minutes", "seconds");
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
