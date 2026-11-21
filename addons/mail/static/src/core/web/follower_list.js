import {
    Component,
    onWillDestroy,
    onWillStart,
    providePlugins,
    signal,
    types,
    usePlugin,
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
import { useVisible } from "@mail/utils/common/hooks";
import { LIST_LOADER_EPOCH, LIST_LOADER_STATUS, ListLoader } from "@mail/utils/common/list_loader";
import { SearchStatePlugin } from "@mail/utils/common/search_state_plugin";

// Past this delay, open the dropdown with a loading indicator if followers are still loading.
export const FOLLOWERS_OPEN_MAX_WAIT = 200;
export const LOAD_MORE_LIMIT = 20;

/**
 * Navigation of the followers dropdown, keeping the scroll of its list when the items change
 * (e.g. Load more, a removed follower): the navigator would otherwise scroll back to its active
 * item. Keyboard navigation still scrolls to the selected item.
 *
 * @param {DropdownState} dropdownState state of the followers dropdown
 */
export function useFollowerListNavigation(dropdownState) {
    const menuRef = signal.ref();
    let listScrollTop;
    const getList = () => menuRef()?.querySelector(".o-mail-FollowerList-list");
    return {
        menuRef,
        navigationOptions: {
            getItems: () => {
                // Called when the items change, before the navigator updates its active item.
                listScrollTop = getList()?.scrollTop;
                const menuEl = dropdownState.isOpen && menuRef();
                return menuEl
                    ? menuEl.querySelectorAll(":scope .o-navigable, :scope .o-dropdown")
                    : [];
            },
            onUpdated: () => {
                const list = getList();
                if (list && listScrollTop !== undefined) {
                    list.scrollTop = listScrollTop;
                }
            },
        },
    };
}

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static components = { Follower, SearchInput };

    followersFullyLoaded = signal(false);
    /** @type {ReturnType<typeof signal<ReturnType<typeof rpc> | undefined>>} */
    pendingFollowersRequest = signal(undefined);
    listRef = signal.ref();
    loadMoreRef = signal.ref();
    searchInputRef = signal.ref();
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
        providePlugins([SearchStatePlugin], {
            fetch: async (searchTerm) => {
                this.pendingFollowersRequest()?.abort();
                this.followersLoader = this._makeLoader(searchTerm);
                await this.loadFollowers();
                return this.followerListView.followers.length > 0;
            },
            isActive: () => !!this.search.searchTerm() || this.search.searching(),
        });
        this.search = usePlugin(SearchStatePlugin);
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
     * Loader of the followers matching `searchTerm`, each page excluding the ones already loaded.
     *
     * @param {string} [searchTerm]
     * @returns {ListLoader}
     */
    _makeLoader(searchTerm) {
        const loader = new ListLoader({
            fetch: (params) => this._fetchPage(searchTerm, params),
            getKnownIds: () =>
                loader.state.older === LIST_LOADER_STATUS.NEW
                    ? []
                    : this.followerListView.followers.map((follower) => follower.id),
            // Fetch one extra follower to show Load more only when another page exists.
            limit: this.LOAD_MORE_LIMIT + 1,
        });
        return loader;
    }

    /**
     * @param {string} [searchTerm] Term used to filter by name or email.
     * @param {import("@mail/utils/common/list_loader").ListLoaderParams} params
     * @returns {Promise<import("models").Follower[]>}
     */
    async _fetchPage(searchTerm, params) {
        const request = rpc("/mail/thread/followers", {
            thread_id: this.props.thread.id,
            thread_model: this.props.thread.model,
            search_term: searchTerm,
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
     * Fetches the next page of `followersLoader`, its first page replacing the list.
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
        const isFirstPage = loader.state.older === LIST_LOADER_STATUS.NEW;
        try {
            const followers = await loader.load(LIST_LOADER_EPOCH.OLDER);
            if (!followers || abortSignal.aborted || loader !== this.followersLoader) {
                return;
            }
            this.followersFullyLoaded.set(!loader.canLoad(LIST_LOADER_EPOCH.OLDER));
            const page = followers.slice(0, this.LOAD_MORE_LIMIT);
            if (isFirstPage) {
                this.followerListView.followers = page;
                this.listRef()?.scrollTo({ top: 0 });
            } else {
                this.followerListView.followers.add(...page);
            }
        } catch (error) {
            if (!(error instanceof ConnectionAbortedError)) {
                throw error;
            }
        }
    }

    onClearSearch() {
        this.search.searchTerm.set("");
        this.searchInputRef()?.focus();
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
