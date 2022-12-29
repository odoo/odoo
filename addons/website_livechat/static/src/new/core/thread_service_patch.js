/** @odoo-module */

import { ThreadService } from "@mail/new/core/thread_service";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "website_livechat", {
    update(thread, data) {
        this._super(thread, data);
        if (data.serverData?.visitor) {
            thread.visitor = this.personaService.insert({
                ...data.serverData.visitor,
                type: "visitor",
            });
        }
    },
});
