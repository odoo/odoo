/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    async fetchData(thread, requestList) {
        const result = await super.fetchData(thread, requestList);
        thread.canSendWhatsapp = result.canSendWhatsapp;
        return result;
    },
});
