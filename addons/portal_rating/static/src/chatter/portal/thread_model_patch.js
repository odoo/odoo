import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

export const REVIEW_INITIAL_LIMIT = 3;
export const REVIEW_LOAD_MORE_LIMIT = 10;

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.selectedRating = false;
        this.ratingChatter = false;
        this.reviewChatter = false;
        this.reviewFetchLimit = REVIEW_INITIAL_LIMIT;
        this._reloadReviews = null;
    },

    getFetchLimit() {
        if (this.reviewChatter) {
            return this.reviewFetchLimit;
        }
        return super.getFetchLimit();
    },

    async fetchMoreMessages({ epoch = "older" } = {}) {
        if (this.reviewChatter && epoch === "older" && this.reviewFetchLimit === REVIEW_INITIAL_LIMIT) {
            return;
        }
        return super.fetchMoreMessages(...arguments);
    },

    getFetchParams() {
        const params = super.getFetchParams(...arguments);
        if (this.ratingChatter) {
            params["rating_include"] = true;
            if (this.selectedRating) {
                params["rating_value"] = this.selectedRating;
            }
        }
        return params;
    },
});
