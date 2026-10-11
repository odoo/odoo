import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

export const threadPatch = patchModel(Thread, {
    computeSelvesBySequence() {
        const result = super.computeSelvesBySequence();
        if (this.portal_partner) {
            result.push({ self: this.portal_partner, sequence: 20 });
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
