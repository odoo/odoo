import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean|undefined} */
        this.hasReadAccess;
    },
    get effectiveSelf() {
        if (this.portal_partner && this.store.self.type !== "partner") {
            return this.portal_partner;
        }
        return super.effectiveSelf;
    },
    /** @deprecated */
    get selves() {
        const result = super.selves;
        if (this.portal_partner) {
            result.push(this.portal_partner);
        }
        return result;
    },
    get rpcParams() {
        return {
            ...super.rpcParams,
            ...(this.access_token ? { token: this.access_token } : {}),
            ...(this.hash ? { hash: this.hash } : {}),
            ...(this.pid ? { pid: this.pid } : {}),
        };
    },
});
