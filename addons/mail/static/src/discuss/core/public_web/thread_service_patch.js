/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    /**
     * @override
     */
    setDiscussThread(thread) {
        super.setDiscussThread(...arguments);
        if (!thread.displayToSelf && thread.model === "discuss.channel") {
            thread.isLocallyPinned = true;
        }
    },
});
