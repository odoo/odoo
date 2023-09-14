/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    get ChatterFetchRoute() {
        return "/mail/chatter_fetch";
    },
});
