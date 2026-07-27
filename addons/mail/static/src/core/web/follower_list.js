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
import { delay } from "@web/core/utils/concurrency";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { ConnectionAbortedError, rpc } from "@web/core/network/rpc";
import { SearchInput } from "@mail/core/common/search_input";
import { Follower } from "@mail/core/web/follower";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { useSearch, useVisible } from "@mail/utils/common/hooks";

// Past this delay, open the dropdown with a loading indicator if followers are still loading.
export const FOLLOWERS_OPEN_MAX_WAIT = 200;
const LOAD_MORE_LIMIT = 20;

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static components = { Follower, SearchInput };

    followersFullyLoaded = signal(false);
    /** @type {ReturnType<typeof signal<ReturnType<typeof rpc> | undefined>>} */
    pendingFollowersRequest = signal(undefined);
    loadMoreRef = signal.ref();
    scope = useScope();

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
        });
        this.search = useSearch({
            fetch: async (searchTerm) => {
                await this.loadFollowers({
                    reset: true,
                    searchTerm,
                });
                return this.followerListView.followers.length > 0;
            },
            isActive: () => this.search.searchTerm || this.search.searching,
        });
        useVisible(this.loadMoreRef, (isVisible) => {
            if (isVisible) {
                this.loadFollowers();
            }
        });
        onWillStart(() => Promise.race([this.loadFollowers(), delay(FOLLOWERS_OPEN_MAX_WAIT)]));
        onWillDestroy(() => {
            this.pendingFollowersRequest()?.abort();
            this.followerListView.delete();
        });
    }

    /**
     * Fetches the next page, or replaces the list and cancels the pending request on reset.
     *
     * Follower records are normalized in the global store, while their ordered
     * relation remains scoped to this `FollowerListView`.
     * @param {Object} [options={}]
     * @param {boolean} [options.reset=false] Whether to replace the loaded followers.
     * @param {string} [options.searchTerm] Term used to filter by name or email.
     */
    async loadFollowers({ reset = false, searchTerm = this.search.searchTerm } = {}) {
        const { abortSignal } = this.scope;
        if (
            !this.props.thread.id ||
            abortSignal.aborted ||
            (!reset && (this.pendingFollowersRequest() || this.followersFullyLoaded()))
        ) {
            return;
        }
        this.pendingFollowersRequest()?.abort();
        const request = rpc("/mail/thread/followers", {
            thread_id: this.props.thread.id,
            thread_model: this.props.thread.model,
            offset: reset ? 0 : this.followerListView.followers.length,
            // Fetch one extra follower to show Load more only when another page exists.
            limit: this.LOAD_MORE_LIMIT + 1,
            search_term: searchTerm,
        });
        this.pendingFollowersRequest.set(request);
        try {
            const { follower_ids, store_data } = await request;
            if (
                abortSignal.aborted ||
                this.pendingFollowersRequest() !== request ||
                searchTerm !== this.search.searchTerm
            ) {
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
        } catch (error) {
            if (!(error instanceof ConnectionAbortedError)) {
                throw error;
            }
        } finally {
            if (this.pendingFollowersRequest() === request) {
                this.pendingFollowersRequest.set(undefined);
            }
        }
    }

    onClearSearch() {
        this.search.searchTerm = "";
    }

    onClickAddFollowers() {
        this.props.dropdown.close();
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

    onClickEdit() {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower: this.props.thread.selfFollower,
            onFollowerChanged: (thread) => this.props.onFollowerChanged?.(thread),
        });
    }

    otherFollowersCount() {
        return this.props.thread.selfFollower
            ? this.props.thread.followersCount - 1
            : this.props.thread.followersCount;
    }
}
