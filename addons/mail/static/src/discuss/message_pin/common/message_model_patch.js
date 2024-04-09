import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";
import { _t } from "@web/core/l10n/translation";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { Message as MessageComponent } from "@mail/core/common/message";

patch(Message.prototype, {
    setup() {
        super.setup();
        /** @type {luxon.DateTime} */
        this.pinned_at = Record.attr(undefined, { type: "datetime" });
    },
    pin() {
        if (this.pinned_at) {
            this.unpin();
        } else {
            this.store.env.services.dialog.add(MessageConfirmDialog, {
                confirmText: _t("Yeah, pin it!"),
                message: this,
                messageComponent: MessageComponent,
                prompt: _t(
                    "You sure want this message pinned to %(conversation)s forever and ever?",
                    {
                        conversation: this.thread.prefix + this.thread.displayName,
                    }
                ),
                size: "md",
                title: _t("Pin It"),
                onConfirm: () => {
                    this.store.env.services.orm.call(
                        "discuss.channel",
                        "set_message_pin",
                        [this.thread.id],
                        { message_id: this.id, pinned: true }
                    );
                },
            });
        }
    },
    unpin() {
        this.store.env.services.dialog.add(MessageConfirmDialog, {
            confirmColor: "btn-danger",
            confirmText: _t("Yes, remove it please"),
            message: this,
            messageComponent: MessageComponent,
            prompt: _t(
                "Well, nothing lasts forever, but are you sure you want to unpin this message?"
            ),
            size: "md",
            title: _t("Unpin Message"),
            onConfirm: () => {
                this.store.env.services.orm.call(
                    "discuss.channel",
                    "set_message_pin",
                    [this.thread.id],
                    { message_id: this.id, pinned: false }
                );
            },
        });
    },
});
