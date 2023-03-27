/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Thread } from "@mail/core_ui/thread";
import { ImStatus } from "@mail/discuss/im_status";
import { useService } from "@web/core/utils/hooks";

patch(Thread.prototype, "website_livechat", {
    setup() {
        this._super();
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.avatarService = useService("mail.avatar");
    },
});

Object.assign(Thread.components, { ImStatus });
