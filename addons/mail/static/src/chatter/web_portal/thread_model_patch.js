import { Thread } from "@mail/core/common/thread_model";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

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
            ...this.rpcParams,
        });
        this.store.insert(result, { html: true });
    },
});
