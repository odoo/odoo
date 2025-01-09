import { Component, useState, onWillUnmount, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FollowerSubtypeDialog } from "./follower_subtype_dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { FollowerList } from "@mail/core/web/follower_list";
import { SearchFollowerInput } from "./search_follower_input";
import { useSequential } from "@mail/utils/common/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * @typedef {Object} Props
 * @property {function} [onAddFollowers]
 * @property {function} [onFollowerChanged]
 * @property {import('@mail/core/common/thread_model').Thread} thread
 * @extends {Component<Props, Env>}
 */

/** @param {import('models').Thread} thread */
export function useFollowerSearch(thread) {
    const sequential = useSequential();
    const store = useService("mail.store");
    const state = useState({
        thread,
        async search() {
            if (this.searchTerm) {
                this.searching = true;
                await sequential(async () => {
                    const res = await rpc("/mail/thread/get_followers", {
                        thread_id: thread.id,
                        thread_model: thread.model,
                        search_term: this.searchTerm,
                    });
                    this.followerListView.searchTerm = this.searchTerm;
                    store.insert(res);
                });
                this.searched = true;
                this.searching = false;
            } else {
                this.clear();
            }
        },
        clear() {
            this.searched = false;
            this.searching = false;
            this.searchTerm = undefined;
        },
        followerListView: undefined,
        /** @type {string|undefined} */
        searchTerm: undefined,
        searched: false,
        searching: false,
    });
    onWillUnmount(() => {
        state.clear();
    });
    return state;
}

export class FollowerListDropDown extends Component {
    static template = "mail.FollowerListDropDown";
    static components = { DropdownItem, Dropdown, FollowerList, SearchFollowerInput };
    static props = ["onAddFollowers?", "onFollowerChanged?", "thread"];

    setup() {
        super.setup();
        this.action = useService("action");
        this.state = useState({
            isSearchOpen: false,
        });
        this.store = useState(useService("mail.store"));
        this.followerSearch = useFollowerSearch(this.props.thread);
        this.followerListDropdown = useDropdownState({
            onOpen: () => {
                this.followerListView.loadFollowers(0);
            },
        });

        onMounted(() => {
            this.followerSearch.followerListView = this.followerListView;
            this.followerListView.loadFollowers();
        });

        onWillUnmount(() => {
            this.followerListView.delete();
        });
    }

    get followerListView() {
        return this.store.FollowerListView.insert({
            threadId: this.props.thread.id,
            threadModel: this.props.thread.model,
        });
    }

    get followerButtonLabel() {
        return _t("Show Followers");
    }

    /**
     * @returns {boolean}
     */
    get isDisabled() {
        return !this.props.thread.id || !this.props.thread.hasReadAccess;
    }

    toggleSearch() {
        if (this.state.isSearchOpen) {
            this.followerSearch.clear();
            this.followerListView.searchTerm = undefined;
            this.followerListView.loadFollowers(0);
        } else {
            this.state.isSearchOpen = !this.state.isSearchOpen;
        }
    }

    onClickAddFollowers() {
        this.followerListDropdown.close();
        const action = {
            type: "ir.actions.act_window",
            res_model: "mail.wizard.invite",
            view_mode: "form",
            views: [[false, "form"]],
            name: _t("Add followers to this document"),
            target: "new",
            context: {
                default_res_model: this.props.thread.model,
                default_res_id: this.props.thread.id,
                dialog_size: "medium",
            },
        };
        this.action.doAction(action, {
            onClose: () => {
                this.props.onAddFollowers?.();
            },
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Follower} follower
     */
    onClickDetails(ev, follower) {
        this.store.openDocument({ id: follower.partner.id, model: "res.partner" });
        this.followerListDropdown.close();
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Follower} follower
     */
    async onClickEdit(ev, follower) {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower,
            onFollowerChanged: () => this.props.onFollowerChanged?.(this.props.thread),
        });
        this.followerListDropdown.close();
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Follower} follower
     */
    async onClickRemove(ev, follower) {
        const thread = this.props.thread;
        await follower.remove();
        this.props.onFollowerChanged?.(thread);
    }
}
