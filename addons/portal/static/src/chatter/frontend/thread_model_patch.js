import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get securityParams() {
        return this.store.env.services["portal.chatter"].portalSecurity;
    },

    getFetchParams() {
        return {
            ...super.getFetchParams(...arguments),
            ...this.securityParams,
        };
    },

    getFetchDataParams(requestList) {
        return {
            ...super.getFetchDataParams(...arguments),
            ...this.securityParams,
        };
    },
});
