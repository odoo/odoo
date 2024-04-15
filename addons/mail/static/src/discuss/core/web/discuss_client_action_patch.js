import { DiscussClientAction } from "@mail/core/web/discuss_client_action";

import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    async restoreDiscussThread() {
        await this.store.channels.fetch();
        return super.restoreDiscussThread(...arguments);
    },
});
