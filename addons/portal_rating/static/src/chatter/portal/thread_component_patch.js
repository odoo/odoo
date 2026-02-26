import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { PortalRatingPlugin } from "@portal_rating/chatter/portal/portal_rating_plugin";
import { REVIEW_LOAD_MORE_LIMIT } from "@portal_rating/chatter/portal/thread_model_patch";
import { Thread as ThreadComponent } from "@mail/core/common/thread";
import { maybePlugin } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadComponent.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalChatter = maybePlugin(PortalChatterPlugin);
        this.portalRating = maybePlugin(PortalRatingPlugin);
    },

    get displayRating() {
        return this.portalChatter?.displayRating() ?? false;
    },

    get reviewChatter() {
        return this.portalRating?.reviewChatter() ?? false;
    },

    onClickLoadOlder() {
        if (this.reviewChatter) {
            this.props.thread.reviewFetchLimit = REVIEW_LOAD_MORE_LIMIT;
        }
        super.onClickLoadOlder();
    },

    get showLoadMore() {
        if (this.reviewChatter) {
            const thread = this.props.thread;
            const total = thread.messages.at(-1)?.rating_stats?.total ?? thread.rating_stats?.total;
            if (total !== undefined) {
                return thread.messages.length < total;
            }
            return thread.loadOlder;
        }
        return super.showLoadMore;
    },

    get loadMoreClass() {
        if (this.displayRating) {
            return { "btn-light": true, "opacity-0": !this.state.mountedAndLoaded };
        }
        return super.loadMoreClass;
    },
});
