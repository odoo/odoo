/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { useMessagePinService } from "@mail/discuss/message_pin/common/message_pin_service";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Message, "discuss/message_pin/common", {
    components: { ...Message.components },
});

patch(Message.prototype, "discuss/message_pin/common", {
    setup() {
        this._super();
        this.messagePinService = useMessagePinService();
    },
    onClickPin() {
        const isPinned = Boolean(this.messagePinService.getPinnedAt(this.message.id));
        if (isPinned) {
            this.messagePinService.unpin(this.message);
        } else {
            this.messagePinService.pin(this.message);
        }
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
