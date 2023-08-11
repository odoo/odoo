/** @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "website_livechat/embed", {
    update(thread, data) {
        this._super(thread, data);
        assignDefined(thread, data, ["requested_by_operator"]);
    },
});
