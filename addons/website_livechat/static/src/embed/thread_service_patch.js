/** @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    update(thread, data) {
        super.update(thread, data);
        assignDefined(thread, data, ["requested_by_operator"]);
    },
});
