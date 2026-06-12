import { Component, props, types } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useVisible } from "@mail/utils/common/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Follower } from "@mail/core/web/follower";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static components = { DropdownItem, Follower };

    setup() {
        super.setup();
        this.action = useService("action");
        this.store = useService("mail.store");
        this.props = props({
            dropdown: types.instanceOf(DropdownState),
            onAddFollowers: types.function([]).optional(),
            onFollowerChanged: types.function([]).optional(),
            thread: types.instanceOf(this.store["mail.thread"].Class),
        });
        useVisible("load-more", (isVisible) => {
            if (isVisible) {
                this.props.thread.loadMoreFollowers();
            }
        });
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
