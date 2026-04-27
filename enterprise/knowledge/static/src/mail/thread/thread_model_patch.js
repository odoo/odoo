import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    /** @type {boolean|undefined} */
    knowledgePreLoading: undefined,
    articleId: undefined,

    /**
     * @override
     */
    async fetchMessagesData({ after, around, before }) {
        if (!this.knowledgePreLoading) {
            return await super.fetchMessagesData(...arguments);
        } else {
            return await this.store.env.services["knowledge.comments"].fetchMessages(this.id);
        }
    },
});
