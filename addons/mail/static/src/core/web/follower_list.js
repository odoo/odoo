import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useVisible } from "@mail/utils/common/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Follower } from "@mail/core/web/follower";

/**
 * @typedef {Object} Props
 * @property {function} [onAddFollowers]
 * @property {function} [onFollowerChanged]
 * @property {import('@mail/core/common/thread_model').Thread} thread
 * @extends {Component<Props, Env>}
 */

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static components = { DropdownItem, Follower };
    static props = ["onAddFollowers?", "onFollowerChanged?", "thread", "dropdown"];

    setup() {
        super.setup();
        this.action = useService("action");
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
}
