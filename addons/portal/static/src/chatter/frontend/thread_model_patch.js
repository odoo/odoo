import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
<<<<<<< 5f8ef4b0b9278e8ad6cf9c355daf7c08fefa7297
||||||| 5a1fff2cc61bd8676049879039defa3fb2a3f13d
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
    get selves() {
        const result = super.selves;
        if (this.portal_partner) {
            result.push(this.portal_partner);
        }
        return result;
    },
=======
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
>>>>>>> 128d52d8437fff794754e730d07d0a877328b927
    get rpcParams() {
        return {
            ...super.rpcParams,
            ...(this.access_token ? { token: this.access_token } : {}),
            ...(this.hash ? { hash: this.hash } : {}),
            ...(this.pid ? { pid: this.pid } : {}),
        };
    },
});
