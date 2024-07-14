/** @odoo-module */

import { Message } from "@mail/core/common/message_model";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    update(data) {
        assignDefined(this, data, ["whatsappStatus"]);
        super.update(data);
    },
    get editable() {
        if (this.originThread?.type === "whatsapp") {
            return false;
        }
        return super.editable;
    },
});
