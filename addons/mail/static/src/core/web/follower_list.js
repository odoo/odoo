import {
    Component,
    onWillDestroy,
    onWillStart,
    signal,
    types,
    useProps,
    useScope,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { ConnectionAbortedError, rpc } from "@web/core/network/rpc";
import { SearchInput } from "@mail/core/common/search_input";
import { Follower } from "@mail/core/web/follower";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { useSearch, useVisible } from "@mail/utils/common/hooks";

const LOAD_MORE_LIMIT = 20;

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static components = { DropdownItem, Follower, SearchInput };

    followersFullyLoaded = signal(false);
    loadMoreRef = signal.ref();
    scope = useScope();
    isLoadingFollowers = false;

    setup() {
        super.setup();
        this.action = useService("action");
        this.store = useService("mail.store");
        this.props = useProps({
            dropdown: types.instanceOf(DropdownState),
            onAddFollowers: types.function([]).optional(),
            onFollowerChanged: types.function([]).optional(),
            thread: types.instanceOf(this.store["mail.thread"]),
        });
        this.LOAD_MORE_LIMIT = LOAD_MORE_LIMIT;
        this.followerListView = this.store.FollowerListView.insert({
            id: uniqueId("follower_list_view_"),
            thread: this.props.thread,
        });
        this.search = useSearch({
            fetch: async (searchTerm) => {
                await this.loadFollowers({
                    abortSignal: this.scope.abortSignal,
                    reset: true,
                    searchTerm,
                });
                return this.followerListView.followers.length > 0;
            },
            isActive: () => this.search.searchTerm || this.search.searching,
        });
        useVisible(this.loadMoreRef, (isVisible) => {
            if (isVisible) {
                this.loadFollowers({ abortSignal: this.scope.abortSignal });
            }
        });
        onWillStart(({ abortSignal }) => this.loadFollowers({ abortSignal }));
        onWillDestroy(() => this.followerListView.delete());
    }

    /**
     * Fetches and appends the next page of followers.
     *
     * Follower records are normalized in the global store, while their ordered
     * relation remains scoped to this `FollowerListView`.
     * @param {Object} [options]
     * @param {AbortSignal} [options.abortSignal] Signal used to cancel the RPC when
     * the component owning this `FollowerListView` is destroyed while the request is still in flight.
     * @param {boolean} [options.reset=false] Whether to replace the loaded followers.
     * @param {string} [options.searchTerm] Term used to filter by name or email.
     */
    loadFollowers({ abortSignal, reset = false, searchTerm = this.search.searchTerm }) {
        if (
            abortSignal.aborted ||
            this.isLoadingFollowers ||
            (!reset && this.followersFullyLoaded())
        ) {
            return;
        }
        this.isLoadingFollowers = true;
        const request = rpc("/mail/thread/followers", {
            thread_id: this.props.thread.id,
            thread_model: this.props.thread.model,
            offset: reset ? 0 : this.followerListView.followers.length,
            // Fetch one extra follower to show Load more only when another page exists.
            limit: this.LOAD_MORE_LIMIT + 1,
            search_term: searchTerm,
        });
        const abortRequest = () => request.abort();
        abortSignal.addEventListener("abort", abortRequest, { once: true });
        return request
            .then(({ follower_ids, store_data }) => {
                if (abortSignal.aborted || searchTerm !== this.search.searchTerm) {
                    return;
                }
                this.store.insert(store_data);
                this.followersFullyLoaded.set(follower_ids.length <= this.LOAD_MORE_LIMIT);
                const followerIds = follower_ids.slice(0, this.LOAD_MORE_LIMIT);
                if (reset) {
                    this.followerListView.followers = followerIds;
                } else {
                    this.followerListView.followers.add(...followerIds);
                }
            })
            .catch((error) => {
                if (!(error instanceof ConnectionAbortedError)) {
                    throw error;
                }
            })
            .finally(() => {
                abortSignal.removeEventListener("abort", abortRequest);
                this.isLoadingFollowers = false;
            });
    }

    onClearSearch() {
        this.search.searchTerm = "";
    }

    onClickAddFollowers() {
        const action = {
            type: "ir.actions.act_window",
            res_model: "mail.followers.edit",
            view_mode: "form",
            views: [[false, "form"]],
            name: _t("Add followers to this document"),
            target: "new",
            context: {
                default_res_model: this.props.thread.model,
                default_res_ids: [this.props.thread.id],
                dialog_size: "medium",
                form_view_ref: "mail.mail_followers_list_edit_form",
            },
        };
        this.action.doAction(action, {
            onClose: () => {
                this.props.onAddFollowers?.();
            },
        });
    }

    async onClickFollow() {
        const { thread } = this.props;
        await thread.follow();
        this.props.onFollowerChanged?.(thread);
    }

    async onClickUnfollow() {
        const { thread } = this.props;
        if (thread.selfFollower) {
            await thread.selfFollower.remove();
            this.props.onFollowerChanged?.(thread);
        }
    }

    async onClickEdit() {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower: this.props.thread.selfFollower,
            onFollowerChanged: (thread) => this.props.onFollowerChanged?.(thread),
        });
        this.props.dropdown.close();
    }

    otherFollowersCount() {
        return this.props.thread.selfFollower
            ? this.props.thread.followersCount - 1
            : this.props.thread.followersCount;
    }
}
