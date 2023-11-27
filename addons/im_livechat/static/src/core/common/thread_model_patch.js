/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(...arguments);
        assignDefined(thread, data, ["operator"]);
        return thread;
    },
});

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.operator = Record.one("Persona");
    },

    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get isChatChannel() {
        return this.type === "livechat" || super.isChatChannel;
    },
});
