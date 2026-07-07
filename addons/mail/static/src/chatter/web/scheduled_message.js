import { AttachmentList } from "@mail/core/common/attachment_list";
import { RelativeTime } from "@mail/core/common/relative_time";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { propComputed } from "@mail/utils/common/hooks";
import { toggleFn } from "@mail/utils/common/signal";

import { Component, signal, t, useProps } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

export const SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD = 50; // arbitrary, ~ 1 line on large screen

/** @param {import("models").Store} store */
export const onScheduledMessageChangedType = (store) =>
    t.function([t.object({ thread: t.instanceOf(store["mail.thread"]) })]);

export class ScheduledMessage extends Component {
    static template = "mail.ScheduledMessage";
    static components = {
        AttachmentList,
        RelativeTime,
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.scheduledMessage = propComputed(
            "scheduledMessage",
            t.instanceOf(this.store["mail.scheduled.message"])
        );
        this.onScheduledMessageChanged = useProps.static(
            "onScheduledMessageChanged",
            onScheduledMessageChangedType(this.store)
        );
        this.onClickAttachmentUnlink = this.onClickAttachmentUnlink.bind(this);
        this.readMore = signal(false);
        this.toggleFn = toggleFn;
        this.avatarCard = usePopover(AvatarCard);
        this.dialogService = useService("dialog");
    }

    get isShort() {
        return this.scheduledMessage().textContent.length < SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD;
    }

    get scheduledDate() {
        return this.scheduledMessage().scheduled_date.toLocaleString(luxon.DateTime.DATETIME_SHORT);
    }

    get truncatedMessage() {
        return (
            this.scheduledMessage().textContent.substring(0, SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD) +
            "..."
        );
    }

    /** @param {{ scheduledMessageAtRender: import("models").ScheduledMessage }} param0 */
    async cancel({ scheduledMessageAtRender }) {
        const thread = scheduledMessageAtRender.thread;
        await scheduledMessageAtRender.cancel();
        this.onScheduledMessageChanged({ thread });
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ scheduledMessageAtRender: import("models").ScheduledMessage }} param1
     */
    onClick(ev, { scheduledMessageAtRender }) {
        this.store.handleClickOnLink(ev, scheduledMessageAtRender.thread);
    }

    /** @type {ReturnType<typeof import("@mail/core/common/attachment_list").unlinkAttachmentType>["type"]} */
    async onClickAttachmentUnlink({ attachment }) {
        attachment.remove();
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ scheduledMessageAtRender: import("models").ScheduledMessage }} param1
     */
    onClickAuthor(ev, { scheduledMessageAtRender }) {
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: scheduledMessageAtRender.author_id.id,
                model: "res.partner",
            });
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ scheduledMessageAtRender: import("models").ScheduledMessage }} param1
     */
    onClickCancel(ev, { scheduledMessageAtRender }) {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure you want to cancel the scheduled message?"),
            cancel: () => {},
            cancelLabel: _t("Close"),
            confirm: () => this.cancel({ scheduledMessageAtRender }),
            confirmLabel: _t("Cancel Message"),
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ scheduledMessageAtRender: import("models").ScheduledMessage }} param1
     */
    async onClickEdit(ev, { scheduledMessageAtRender }) {
        const thread = scheduledMessageAtRender.thread;
        await scheduledMessageAtRender.edit();
        this.onScheduledMessageChanged({ thread });
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ scheduledMessageAtRender: import("models").ScheduledMessage }} param1
     */
    async onClickSendNow(ev, { scheduledMessageAtRender }) {
        const thread = scheduledMessageAtRender.thread;
        await scheduledMessageAtRender.send();
        this.onScheduledMessageChanged({ thread });
    }
}
