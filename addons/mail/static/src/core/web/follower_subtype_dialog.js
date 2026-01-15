import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

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

    get title() {
        return _t("Edit Subscription of %(name)s", { name: this.props.follower.displayName });
    }
}
