/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Message, {
    components: { ...Message.components },
});

patch(Message.prototype, {
    setup() {
        super.setup();
        this.messagePinService = useState(useService("discuss.message.pin"));
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
        const res = super.attClass;
        return Object.assign(res, {
            "o-cancelSelfAuthored": this.env.pinnedPanel,
            "mt-1": res["mt-1"] && !this.env.pinnedPanel,
            "px-3": res["px-3"] && !this.env.pinnedPanel,
        });
    },
    get isAlignedRight() {
        return !this.env.pinnedPanel && super.isAlignedRight;
    },
    getPinOptionText() {
        return this.messagePinService.getPinnedAt(this.message.id) ? _t("Unpin") : _t("Pin");
    },
    get shouldDisplayAuthorName() {
        if (this.env.pinnedPanel) {
            return true;
        }
        return super.shouldDisplayAuthorName;
    },
});
