import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    /** @param {string[]} requestList */
    async fetchThreadData(requestList) {
        if (requestList.includes("messages")) {
            this.fetchNewMessages();
        }
        await this.store.fetchStoreData("mail.thread", {
            access_params: this.rpcParams,
            request_list: requestList,
            thread_id: this.id,
            thread_model: this.model,
        });
    },
});
