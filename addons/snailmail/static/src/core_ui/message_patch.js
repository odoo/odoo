import { Message } from "@mail/core/common/message";

import { SnailmailError } from "./snailmail_error";
import { SnailmailNotificationPopover } from "./snailmail_notification_popover";

import { patch } from "@web/core/utils/patch";

import { toRaw } from "@odoo/owl";

patch(Message.prototype, {
    onClickNotification(ev) {
        // Keep the original notification click logic of opening the failure popover
        if (this.message.message_type === "snailmail" && toRaw(this.message).failureNotifications.length > 0) {
            this.onClickFailure(ev);
        } else {
            super.onClickNotification(ev);
        }
    },
    onClickFailure() {
        if (this.message.message_type === "snailmail") {
            const failureType = this.message.notification_ids[0].failure_type;
            switch (failureType) {
                case "sn_credit":
                case "sn_trial":
                case "sn_price":
                case "sn_error":
                    this.env.services.dialog.add(SnailmailError, {
                        failureType: failureType,
                        messageId: this.message.id,
                    });
                    break;
                case "sn_fields":
                    this.openMissingFieldsLetterAction();
                    break;
                case "sn_format":
                    this.openFormatLetterAction();
                    break;
            }
        } else {
            super.onClickFailure(...arguments);
        }
    },

    async openMissingFieldsLetterAction() {
        const letterIds = await this.env.services.orm.searchRead(
            "snailmail.letter",
            [["message_id", "=", this.message.id]],
            ["id"]
        );
        this.env.services.action.doAction(
            "snailmail.snailmail_letter_missing_required_fields_action",
            {
                additionalContext: {
                    default_letter_id: letterIds[0].id,
                },
            }
        );
    },

    openFormatLetterAction() {
        this.env.services.action.doAction("snailmail.snailmail_letter_format_error_action", {
            additionalContext: {
                message_id: this.message.id,
            },
        });
    },
});

Message.components = {
    ...Message.components,
    Popover: SnailmailNotificationPopover,
    SnailmailError,
};
