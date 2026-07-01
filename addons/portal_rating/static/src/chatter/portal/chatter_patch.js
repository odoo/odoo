import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { patch } from "@web/core/utils/patch";

const chatterPatch = {
    get extraMessageFetchRouteParams() {
        const params = super.extraMessageFetchRouteParams;
        if (this.env.inFrontendPortalChatter && this.state.thread?.selectedRating) {
            params.rating_value = this.state.thread.selectedRating;
        }
        return params;
    },

    async onClickStarDomain(star) {
        const { thread } = this.state;
        Object.assign(thread, {
            loadOlder: false,
            rating_stats: this.ratingStats,
            selectedRating: star,
        });
        thread.messages = await thread.fetchMessages({ routeParams: this.messageFetchRouteParams });
        thread.loadOlder = thread.messages.length === this.store.FETCH_LIMIT;
    },

    async onClickStarDomainReset() {
        const { thread } = this.state;
        Object.assign(thread, {
            loadOlder: false,
            selectedRating: false,
        });
        thread.messages = await thread.fetchMessages({ routeParams: this.messageFetchRouteParams });
        thread.loadOlder = thread.messages.length === this.store.FETCH_LIMIT;
    },

    get ratingStats() {
        return this.state.thread?.rating_stats;
    },
};

patch(Chatter.prototype, chatterPatch);
