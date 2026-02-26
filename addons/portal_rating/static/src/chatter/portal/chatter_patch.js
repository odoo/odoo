import { browser } from "@web/core/browser/browser";
import { PortalRatingPlugin } from "@portal_rating/chatter/portal/portal_rating_plugin";
import { REVIEW_INITIAL_LIMIT } from "@portal_rating/chatter/portal/thread_model_patch";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { maybePlugin } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

const chatterPatch = {
    setup() {
        super.setup(...arguments);
        this.state.showReviewComposer = false;
        this.portalRating = maybePlugin(PortalRatingPlugin);
    },

    get reviewChatter() {
        return this.portalRating?.reviewChatter() ?? false;
    },

    get requestList() {
        if (this.displayRating) {
            return ["messages"];
        }
        return super.requestList;
    },

    changeThread() {
        super.changeThread(...arguments);
        if (this.displayRating && this.state.thread) {
            this.state.thread.ratingChatter = true;
            this.state.thread.reviewChatter = this.reviewChatter;
            this.state.thread._reloadReviews = () => this._reloadReviews(this.state.thread);
        }
    },

    async _reloadReviews(thread, { preserveStats = false } = {}) {
        const prevStats = this.ratingStats;
        thread.reviewFetchLimit = REVIEW_INITIAL_LIMIT;
        thread.isLoaded = false;
        thread.messages.splice(0, thread.messages.length);
        await thread.fetchNewMessages();
        if (preserveStats && !thread.messages.length) {
            thread.rating_stats = prevStats;
        }
    },

    async onReviewPostCallback() {
        this.state.showReviewComposer = false;
        const { thread } = this.state;
        thread.selectedRating = false;
        await this._reloadReviews(thread);
    },

    async onClickStarDomain(star) {
        const { thread } = this.state;
        thread.selectedRating = star;
        await this._reloadReviews(thread, { preserveStats: true });
    },

    async onClickStarDomainReset() {
        const { thread } = this.state;
        thread.selectedRating = false;
        await this._reloadReviews(thread);
    },

    get ratingStats() {
        return this.state.thread?.messages.at(-1)?.rating_stats || this.state.thread?.rating_stats;
    },

    get threadShowDates() {
        return !this.displayRating;
    },

    get loginRedirectUrl() {
        return `/web/login?redirect=${encodeURIComponent(browser.location.pathname)}#discussion`;
    },
};

patch(Chatter.prototype, chatterPatch);
