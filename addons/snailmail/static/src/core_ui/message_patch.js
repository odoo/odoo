/** @odoo-module */

import { Message } from "@mail/core/common/message";

import { SnailmailError } from "./snailmail_error";
import { SnailmailNotificationPopover } from "./snailmail_notification_popover";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    onClickFailure() {
        if (this.message.message_type === "snailmail") {
            const failureType = this.message.notifications[0].failure_type;
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
