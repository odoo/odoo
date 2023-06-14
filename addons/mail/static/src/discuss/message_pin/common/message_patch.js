/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import {
    getMessagePinnedAt,
    setPinOnMessage,
} from "@mail/discuss/message_pin/common/message_pin_service";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";

patch(Message, "discuss/message_pin/common", {
    components: { ...Message.components },
});

patch(Message.prototype, "discuss/message_pin/common", {
    onClickPin() {
        const pinnedAt = getMessagePinnedAt(this.message.id);
        const thread = this.message.originThread;
        this.env.services.dialog.add(MessageConfirmDialog, {
            confirmColor: pinnedAt ? "btn-danger" : undefined,
            confirmText: pinnedAt ? _t("Yes, remove it please") : _t("Yeah, pin it!"),
            message: this.message,
            messageComponent: Message,
            prompt: pinnedAt
                ? _t("Well nothing lasts forever, but are you sure you want to unpin this message?")
                : sprintf(
                      _t("You sure want this message pinned to %(conversation)s forever and ever?"),
                      { conversation: thread.prefix + thread.displayName }
                  ),
            size: "md",
            title: pinnedAt ? _t("Unpin Message") : _t("Pin It"),
            onConfirm: () => setPinOnMessage(this.message, !getMessagePinnedAt(this.message.id)),
        });
    },
    get attClass() {
        const res = this._super();
        return Object.assign(res, {
            "o-cancelSelfAuthored": this.env.pinnedPanel,
            "mt-1": res["mt-1"] && !this.env.pinnedPanel,
            "px-3": res["px-3"] && !this.env.pinnedPanel,
        });
    },
    get isAlignedRight() {
        return !this.env.pinnedPanel && this._super();
    },
    get pinOptionText() {
        return getMessagePinnedAt(this.message.id) ? _t("Unpin") : _t("Pin");
    },
    get shouldDisplayAuthorName() {
        if (this.env.pinnedPanel) {
            return true;
        }
        return this._super();
    },
});
