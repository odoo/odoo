import { Thread } from "@mail/core/common/thread_model";
import { rpcWithEnv } from "@mail/utils/common/misc";
/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import { patch } from "@web/core/utils/patch";

patch(Thread, {
    new() {
        rpc = rpcWithEnv(this.env);
        return super.new(...arguments);
    },
});
patch(Thread.prototype, {
    /** @param {string[]} requestList */
    async fetchData(requestList) {
        if (requestList.includes("messages")) {
            this.fetchNewMessages();
        }
        const result = await rpc("/mail/thread/data", {
            request_list: requestList,
            thread_id: this.id,
            thread_model: this.model,
        });
        this.store.Thread.insert(result, { html: true });
        return result;
    },
});
