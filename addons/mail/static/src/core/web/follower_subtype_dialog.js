import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

/**
 * @typedef {Object} Props
 * @property {function} close
 * @property {import("models").Follower} follower
 * @property {function} onFollowerChanged
 * @extends {Component<Props, Env>}
 */
export class FollowerSubtypeDialog extends Component {
    static components = { Dialog };
    static props = ["close", "follower", "onFollowerChanged"];
    static template = "mail.FollowerSubtypeDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            /** @type {import("models").MailMessageSubtype[]} */
            subtypes: [],
        });
        onWillStart(async () => {
            const { store_data, subtype_ids } = await rpc("/mail/read_subscription_data", {
                follower_id: this.props.follower.id,
            });
            this.store.insert(store_data);
            this.state.subtypes = subtype_ids.map((id) =>
                this.store["mail.message.subtype"].get(id)
            );
        });
    }

    /**
     * @param {Event} ev
     * @param {SubtypeData} subtype
     */
    onChangeCheckbox(ev, subtype) {
        if (ev.target.checked) {
            this.props.follower.subtype_ids.add(subtype);
        } else {
            this.props.follower.subtype_ids.delete(subtype);
        }
    }

    async onClickApply() {
        const selectedSubtypes = this.state.subtypes.filter((s) =>
            s.in(this.props.follower.subtype_ids)
        );
        if (selectedSubtypes.length === 0) {
            await this.props.follower.remove();
        } else {
            await this.env.services.orm.call(
                this.props.follower.thread.model,
                "message_subscribe",
                [[this.props.follower.thread.id]],
                {
                    partner_ids: [this.props.follower.partner_id.id],
                    subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                }
            );
            if (this.store.mt_comment.notIn(selectedSubtypes)) {
                this.props.follower.removeRecipient();
            }
            this.env.services.notification.add(
                _t("The subscription preferences were successfully applied."),
                { type: "success" }
            );
        }
        this.props.onFollowerChanged();
        this.props.close();
    }

    async addCustomSubtype() {
        return this.env.services.action.doAction(
            {
                name: _t("Create Custom Subtype"),
                type: "ir.actions.act_window",
                res_model: "mail.custom.message.subtype",
                views: [[false, "form"]],
                view_mode: "form",
                target: "new",
                context: {
                    default_res_model: this.props.follower.thread.model,
                    default_model: this.props.follower.thread.model,
                },
            },
            {
                onClose: async (infos) => {
                    if (!infos || infos.special || infos.dismiss) {
                        return;
                    }
                    this.notification.add(_t("Notification added"), {
                        type: "success",
                    });
                    this.store.insert(infos.store_data);
                    this.state.subtypes.push(
                        this.store["mail.message.subtype"].get(infos.subtype_id)
                    );
                },
            }
        );
    }

    async editCustomSubtype(subtype) {
        return this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.message.subtype",
            views: [[false, "form"]],
            view_mode: "form",
            res_id: subtype.id,
            target: "current",
        });
    }

    get title() {
        return _t("Edit Subscription of %(name)s", { name: this.props.follower.partner_id.name });
    }

    get isForSelf() {
        return this.props.follower.partner_id.id === user.partnerId;
    }
}
