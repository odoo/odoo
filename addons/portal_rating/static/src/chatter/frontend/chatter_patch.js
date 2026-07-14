import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

const chatterPatch = {
    async onClickStarDomain(star) {
        const { thread } = this.state;
        Object.assign(thread, {
            loadOlder: false,
            rating_stats: this.ratingStats,
            selectedRating: star,
        });
        thread.messages = await thread.fetchMessages();
        thread.loadOlder = thread.messages.length === this.store.FETCH_LIMIT;
    },

    async onClickStarDomainReset() {
        const { thread } = this.state;
        Object.assign(thread, {
            loadOlder: false,
            selectedRating: false,
        });
        thread.messages = await thread.fetchMessages();
        thread.loadOlder = thread.messages.length === this.store.FETCH_LIMIT;
    },

    get ratingStats() {
        return this.state.thread?.messages.at(-1)?.rating_stats || this.state.thread?.rating_stats;
    },
};

patch(Chatter.prototype, chatterPatch);
