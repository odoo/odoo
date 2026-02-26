import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { Thread as ThreadComponent } from "@mail/core/common/thread";
import { maybePlugin } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadComponent.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalChatterPlugin = maybePlugin(PortalChatterPlugin);
    },

    get displayRating() {
        return this.portalChatterPlugin?.displayRating() ?? false;
    },

    get shouldTriggerLoadOnVisible() {
        if (
            this.props.thread.reviewChatter &&
            this.props.thread.persistentMessages.length <= this.props.thread.initialFetchLimit
        ) {
            return false;
        }
        return super.shouldTriggerLoadOnVisible;
    },

    get loadOlderWrapperAttClass() {
        return {
            ...super.loadOlderWrapperAttClass,
            "d-flex align-items-center gap-2 px-2": this.displayRating,
        };
    },

    get loadMoreBtnClass() {
        return this.displayRating ? "btn btn-light" : super.loadMoreBtnClass;
    },

    get showLoadOlder() {
        if (!this.props.thread.reviewChatter) {
            return super.showLoadOlder;
        }
        const stats = this.props.thread.rating_stats;
        if (!stats) {
            return false;
        }
        const total = this.props.thread.selectedRating
            ? Math.round((stats.percent[this.props.thread.selectedRating] * stats.total) / 100)
            : stats.total;
        return (
            this.props.thread.isLoaded &&
            !this.props.thread.isTransient &&
            !this.props.thread.hasLoadingFailed &&
            this.props.thread.persistentMessages.length < total
        );
    },
});
