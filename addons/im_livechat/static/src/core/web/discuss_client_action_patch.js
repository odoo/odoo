import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";

import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    async restoreDiscussThread() {
        if (this.store.has_access_livechat) {
            this.store.livechatChannels.fetch();
        }
        return super.restoreDiscussThread(...arguments);
    },
});
