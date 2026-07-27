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
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { ConnectionAbortedError, rpc } from "@web/core/network/rpc";
import { Follower } from "@mail/core/web/follower";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { useVisible } from "@mail/utils/common/hooks";
import { LIST_LOADER_EPOCH, ListLoader } from "@mail/utils/common/list_loader";

// Past this delay, open the dropdown with a loading indicator if followers are still loading.
export const FOLLOWERS_OPEN_MAX_WAIT = 200;
const LOAD_MORE_LIMIT = 20;

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static components = { DropdownItem, Follower };

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
        this.followersLoader = this._makeLoader();
        useVisible(this.loadMoreRef, (isVisible) => {
            if (isVisible) {
                this.loadFollowers();
            }
        });
        onWillStart(() => {
            const { promise, resolve } = Promise.withResolvers();
            this.loadFollowers().finally(resolve);
            return Promise.race([promise, delay(FOLLOWERS_OPEN_MAX_WAIT)]);
        });
        onWillDestroy(() => {
            this.pendingFollowersRequest()?.abort();
            this.followerListView.delete();
        });
    }

    /**
     * Loader of the followers, each page excluding the ones already loaded.
     *
     * @returns {ListLoader}
     */
    _makeLoader() {
        return new ListLoader({
            fetch: (params) => this._fetchPage(params),
            getKnownIds: () => this.followerListView.followers.map((follower) => follower.id),
            // Fetch one extra follower to show Load more only when another page exists.
            limit: this.LOAD_MORE_LIMIT + 1,
        });
    }

    /**
     * @param {import("@mail/utils/common/list_loader").ListLoaderParams} params
     * @returns {Promise<import("models").Follower[]>}
     */
    async _fetchPage(params) {
        const request = rpc("/mail/thread/followers", {
            thread_id: this.props.thread.id,
            thread_model: this.props.thread.model,
            ...params,
        });
        this.pendingFollowersRequest.set(request);
        try {
            const { follower_ids, store_data } = await request;
            this.store.insert(store_data);
            return follower_ids.map((id) => this.store["mail.followers"].get(id));
        } finally {
            if (this.pendingFollowersRequest() === request) {
                this.pendingFollowersRequest.set(undefined);
            }
        }
    }

    /**
     * Fetches and appends the next page of followers.
     *
     * Follower records are normalized in the global store, while their ordered
     * relation remains scoped to this `FollowerListView`.
     */
    async loadFollowers() {
        const { abortSignal } = this.scope;
        if (!this.props.thread.id || abortSignal.aborted) {
            return;
        }
        const loader = this.followersLoader;
        try {
            const followers = await loader.load(LIST_LOADER_EPOCH.OLDER);
            if (!followers || abortSignal.aborted) {
                return;
            }
            this.followersFullyLoaded.set(!loader.canLoad(LIST_LOADER_EPOCH.OLDER));
            this.followerListView.followers.add(...followers.slice(0, this.LOAD_MORE_LIMIT));
        } catch (error) {
            if (!(error instanceof ConnectionAbortedError)) {
                throw error;
            }
        }
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
}
