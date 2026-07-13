/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread, {
    get onlineMemberStatuses() {
        return [...super.onlineMemberStatuses, "leave_online", "leave_away"];
    },
});
