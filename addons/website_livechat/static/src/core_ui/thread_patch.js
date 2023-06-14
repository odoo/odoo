/* @odoo-module */

import { Thread } from "@mail/core/common/thread";
import { ImStatus } from "@mail/core/common/im_status";
import { patch } from "@web/core/utils/patch";
import { avatarUrl } from "@mail/core/common/thread_service";

Object.assign(Thread.components, { ImStatus });

patch(Thread.prototype, "website_livechat", {
    setup(...args) {
        this._super(...args);
        this.avatarUrl = avatarUrl;
    },
});
