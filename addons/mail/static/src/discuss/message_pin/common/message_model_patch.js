import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/core/common/record";
import { _t } from "@web/core/l10n/translation";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { Deferred } from "@web/core/utils/concurrency";

patch(Message.prototype, {
    setup() {
        super.setup();
        this.pinned_at = fields.Datetime();
    },
    /** @returns {Deferred<boolean>} */
    pin() {
        if (this.pinned_at) {
            return this.unpin();
        }
        const def = new Deferred();
        this.store.env.services.dialog.add(
            MessageConfirmDialog,
            {
                confirmText: _t("Yeah, pin it!"),
                message: this,
                prompt: _t(
                    "You sure want this message pinned to %(conversation)s forever and ever?",
                    {
                        conversation: this.thread.prefix + this.thread.displayName,
                    }
                ),
                size: "md",
                title: _t("Pin It"),
                onConfirm: () => {
                    def.resolve(true);
                    this.store.env.services.orm.call(
                        "discuss.channel",
                        "set_message_pin",
                        [this.thread.id],
                        { message_id: this.id, pinned: true }
                    );
                },
            },
            { onClose: () => def.resolve(false) }
        );
        return def;
    },
    /** @returns {Deferred<boolean>} */
    unpin() {
        const def = new Deferred();
        this.store.env.services.dialog.add(
            MessageConfirmDialog,
            {
                confirmColor: "btn-danger",
                confirmText: _t("Yes, remove it please"),
                message: this,
                prompt: _t(
                    "Well, nothing lasts forever, but are you sure you want to unpin this message?"
                ),
                size: "md",
                title: _t("Unpin Message"),
                onConfirm: () => {
                    def.resolve(true);
                    this.store.env.services.orm.call(
                        "discuss.channel",
                        "set_message_pin",
                        [this.thread.id],
                        { message_id: this.id, pinned: false }
                    );
                },
            },
            { onClose: () => def.resolve(false) }
        );
        return def;
    },
});
