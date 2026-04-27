/** @odoo-module **/

import { StreamPostDashboard } from "@social/js/stream_post_kanban_dashboard";
import { patch } from "@web/core/utils/patch";

patch(StreamPostDashboard.prototype, {
    /**
     * We do not want to display stories information for Facebook account.
     * @override
     */
    _hasStories(account) {
        return account.media_type !== "facebook" && super._hasStories(...arguments);
    },
});
