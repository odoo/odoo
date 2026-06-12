import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, props, signal, types } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class FollowerSubtypeDialog extends Component {
    static components = { Dialog };
    static template = "mail.FollowerSubtypeDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            close: types.function([types.instanceOf(MouseEvent)]),
            follower: types.instanceOf(this.store["mail.followers"].Class),
            onFollowerChanged: types.function([]),
        });
        this.subtypes = signal(null, {
            type: types.array(types.instanceOf(this.store["mail.message.subtype"].Class)),
        });
        onWillStart(async () => {
            const { store_data, subtype_ids } = await rpc("/mail/read_subscription_data", {
                follower_id: this.props.follower.id,
            });
            this.store.insert(store_data);
            this.subtypes.set(subtype_ids.map((id) => this.store["mail.message.subtype"].get(id)));
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
        const thread = this.props.follower.thread;
        const selectedSubtypes = this.subtypes().filter((s) =>
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
            this.env.services.notification.add(_t("Notification preferences updated."), {
                type: "success",
            });
        }
        this.props.onFollowerChanged(thread);
        this.props.close();
    }

    get title() {
        return _t("Notification Preferences");
    }
}
