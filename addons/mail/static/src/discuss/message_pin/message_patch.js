/* @odoo-module */

import { Message } from "@mail/core_ui/message";
import { MessageConfirmDialog } from "@mail/core_ui/message_confirm_dialog";
import { useMessagePinService } from "@mail/discuss/message_pin/message_pin_service";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Message, "discuss/message_pin", {
    components: { ...Message.components },
});

patch(Message.prototype, "discuss/message_pin", {
    setup() {
        this._super();
        this.messagePinService = useMessagePinService();
    },
    onClickPin() {
        const prompt = this.messagePinService.getPinnedAt(this.message.id)
            ? _t("Are you sure you want to remove this pinned message?")
            : _t(
                  "The following message will be pinned to the channel. Are you sure you want to continue?"
              );
        this.env.services.dialog.add(MessageConfirmDialog, {
            message: this.message,
            messageComponent: Message,
            prompt,
            onConfirm: () =>
                this.messagePinService.setPin(
                    this.message,
                    !this.messagePinService.getPinnedAt(this.message.id)
                ),
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
        return this.messagePinService.getPinnedAt(this.message.id) ? _t("Unpin") : _t("Pin");
    },
    get shouldDisplayAuthorName() {
        if (this.env.pinnedPanel) {
            return true;
        }
        return this._super();
    },
});
