import { useForwardRefsToParent } from "@mail/utils/common/hooks";
import { Component, htmlEscape, markup, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class NotificationMessage extends Component {
    static template = "mail.NotificationMessage";

    setup() {
        super.setup();
        this.rootRef = signal();
        useForwardRefsToParent("messageRefs", (props) => props.message.id, this.rootRef);
        this.htmlEscape = htmlEscape;
        this.store = useService("mail.store");
        this.props = useProps({
            message: t.instanceOf(this.store["mail.message"]),
            messageRefs: t.instanceOf(Map).optional(),
            thread: t.instanceOf(this.store["mail.thread"]),
        });
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
                })
            );
        }
    }

    get message() {
        return this.props.message;
    }

    callHistory() {
        return this.message.call_history_ids[0];
    }

    recordingInformation() {
        const history = this.callHistory();
        return _t(
            "A recording is being processed and will be available %(anchor_start)shere%(anchor_end)s.",
            {
                anchor_start: markup`<a href="/odoo/discuss.call.history/${history.id}" data-oe-model="discuss.call.history" data-oe-id="${history.id}">`,
                anchor_end: markup`</a>`,
            }
        );
    }

    get showDate() {
        return true;
    }

    get callInformation() {
        const history = this.callHistory();
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

    get pinInformation() {
        return _t(
            "%(user)s pinned %(message_link_start)sa message%(message_link_end)s to this channel.",
            {
                user: this.message.authorName,
                message_link_start: markup`<a href="#" data-oe-type="highlight" data-oe-id="${this.message.pinnedMessageId}">`,
                message_link_end: markup`</a>`,
            }
        );
    }

    get seeAllPinsInformation() {
        return _t("See %(pins_link_start)sall pinned messages%(pins_link_end)s.", {
            pins_link_start: markup`<a href="#" data-oe-type="pin-menu">`,
            pins_link_end: markup`</a>`,
        });
    }

    get showInlineBody() {
        return [
            "channel_rename",
            "meeting_to_group_chat",
            "thread_deletion",
            "thread_creation",
        ].includes(this.message.notificationType);
    }
}
