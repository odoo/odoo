import { Component, useState, onWillUnmount, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FollowerSubtypeDialog } from "./follower_subtype_dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { FollowerList } from "@mail/core/web/follower_list";

/**
 * @typedef {Object} Props
 * @property {function} [onAddFollowers]
 * @property {function} [onFollowerChanged]
 * @property {import('@mail/core/common/thread_model').Thread} thread
 * @extends {Component<Props, Env>}
 */

export class FollowerListDropDown extends Component {
    static template = "mail.FollowerListDropDown";
    static components = { DropdownItem, Dropdown, FollowerList };
    static props = ["onAddFollowers?", "onFollowerChanged?", "thread"];

    setup() {
        super.setup();
        this.action = useService("action");
        this.store = useState(useService("mail.store"));
        this.followerListDropdown = useDropdownState({
            onOpen: () => {
                this.followerListView.loadFollowers(0);
            },
        });

        onMounted(() => {
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

    onClickAddFollowers() {
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
