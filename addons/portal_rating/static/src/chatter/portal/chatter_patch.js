import { browser } from "@web/core/browser/browser";
import { PortalRatingPlugin } from "@portal_rating/chatter/portal/portal_rating_plugin";
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
        }
    },

    reloadReviews(thread) {
        this.env.bus.trigger("MAIL:RELOAD-THREAD", { model: thread.model, id: thread.id });
    },

    onReviewPostCallback() {
        this.state.showReviewComposer = false;
        const { thread } = this.state;
        thread.selectedRating = false;
        this.reloadReviews(thread);
    },

    onClickStarDomain(star) {
        const { thread } = this.state;
        thread.selectedRating = star;
        this.reloadReviews(thread);
    },

    onClickStarDomainReset() {
        const { thread } = this.state;
        thread.selectedRating = false;
        this.reloadReviews(thread);
    },

    get ratingStats() {
        return this.state.thread?.rating_stats;
    },

    get threadShowDates() {
        return !this.displayRating;
    },

    get loginRedirectUrl() {
        return `/web/login?redirect=${encodeURIComponent(browser.location.pathname)}#discussion`;
    },
};

patch(Chatter.prototype, chatterPatch);
