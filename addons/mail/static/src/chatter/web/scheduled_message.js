import { AttachmentList } from "@mail/core/common/attachment_list";
import { RelativeTime } from "@mail/core/common/relative_time";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

import { Component, useState } from "@odoo/owl";

export const SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD = 50; // arbitrary, ~ 1 line on large screen

export class ScheduledMessage extends Component {
    static props = {
        onScheduledMessageChanged: Function,
        scheduledMessage: Object,
    };
    static template = "mail.ScheduledMessage";
    static components = {
        AttachmentList,
        RelativeTime,
    };

    setup() {
        super.setup();
        this.state = useState({
            readMore: false,
        });
        this.avatarCard = usePopover(AvatarCardPopover);
        this.dialogService = useService("dialog");
    }

    get isShort() {
        return (
            this.props.scheduledMessage.textContent.length < SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD
        );
    }

    get scheduledDate() {
        return this.props.scheduledMessage.scheduled_date.toLocaleString(
            luxon.DateTime.DATETIME_SHORT
        );
    }

    get truncatedMessage() {
        return (
            this.props.scheduledMessage.textContent.substring(
                0,
                SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD
            ) + "..."
        );
    }

    async cancel() {
        const thread = this.props.scheduledMessage.thread;
        await this.props.scheduledMessage.cancel();
        this.props.onScheduledMessageChanged(thread);
    }

    onClick(ev) {
        this.props.scheduledMessage.store.handleClickOnLink(ev, this.props.scheduledMessage.thread);
    }

    async onClickAttachmentUnlink(attachment) {
        attachment.remove();
    }

    onClickAuthor(ev) {
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: this.props.scheduledMessage.author_id.main_user_id?.id,
            });
        }
    }

    onClickCancel() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure you want to cancel the scheduled message?"),
            cancel: () => {},
            cancelLabel: _t("Close"),
            confirm: this.cancel.bind(this),
            confirmLabel: _t("Cancel Message"),
        });
    }

    async onClickEdit() {
        await this.props.scheduledMessage.edit();
        this.props.onScheduledMessageChanged(this.props.scheduledMessage.thread);
    }

    async onClickSendNow() {
        await this.props.scheduledMessage.send();
        this.props.onScheduledMessageChanged(this.props.scheduledMessage.thread);
    }
}
