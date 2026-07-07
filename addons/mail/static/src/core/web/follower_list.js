import { Component, signal, types, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { propComputed, useVisible } from "@mail/utils/common/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Follower } from "@mail/core/web/follower";
import { onFollowerChangedType } from "@mail/core/web/follower_types";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static components = { DropdownItem, Follower };

    loadMoreRef = signal.ref();

    setup() {
        super.setup();
        this.action = useService("action");
        this.store = useService("mail.store");
        this.onFollowerChanged = useProps.static(
            "onFollowerChanged",
            onFollowerChangedType(this.store).optional()
        );
        this.dropdown = propComputed("dropdown", types.instanceOf(DropdownState));
        this.onAddFollowers = useProps.static(
            "onAddFollowers",
            onFollowerChangedType(this.store).optional()
        );
        this.thread = propComputed("thread", types.instanceOf(this.store["mail.thread"]));
        useVisible(this.loadMoreRef, (isVisible) => {
            if (isVisible) {
                this.thread().loadMoreFollowers();
            }
        });
    }

    /** @param {{ threadAtRender: import("models").Thread }} param0 */
    onClickAddFollowers({ threadAtRender }) {
        const action = {
            type: "ir.actions.act_window",
            res_model: "mail.followers.edit",
            view_mode: "form",
            views: [[false, "form"]],
            name: _t("Add followers to this document"),
            target: "new",
            context: {
                default_res_model: threadAtRender.model,
                default_res_ids: [threadAtRender.id],
                dialog_size: "medium",
                form_view_ref: "mail.mail_followers_list_edit_form",
            },
        };
        this.action.doAction(action, {
            onClose: () => {
                this.onAddFollowers?.({ thread: threadAtRender });
            },
        });
    }

    /** @param {{ threadAtRender: import("models").Thread }} param0 */
    async onClickFollow({ threadAtRender }) {
        await threadAtRender.follow();
        this.onFollowerChanged?.({ thread: threadAtRender });
    }

    /** @param {{ threadAtRender: import("models").Thread }} param0 */
    async onClickUnfollow({ threadAtRender }) {
        if (threadAtRender.selfFollower) {
            await threadAtRender.selfFollower.remove();
            this.onFollowerChanged?.({ thread: threadAtRender });
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ threadAtRender: import("models").Thread }} param1
     */
    async onClickEdit(ev, { threadAtRender }) {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower: threadAtRender.selfFollower,
            /** @type {ReturnType<typeof import("@mail/core/web/follower_types").onFollowerChangedType>["type"]} */
            onFollowerChanged: ({ thread }) => this.onFollowerChanged?.({ thread }),
        });
        this.dropdown().close();
    }
}
