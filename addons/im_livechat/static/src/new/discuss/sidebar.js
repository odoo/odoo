/** @odoo-module */

import { Sidebar } from "@mail/new/web/discuss/sidebar";
import { patch } from "@web/core/utils/patch";

patch(Sidebar.prototype, "im_livechat", {
    get shouldDisplayLivechatCategory() {
        return this.store.discuss.livechat.threads.some(
            (localId) => this.store.threads[localId]?.is_pinned
        );
    },
});
