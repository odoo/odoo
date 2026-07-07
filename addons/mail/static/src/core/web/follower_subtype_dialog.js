import { onFollowerChangedType } from "@mail/core/web/follower_types";
import { propComputed } from "@mail/utils/common/hooks";

import { rpc } from "@web/core/network/rpc";
import { asyncComputed, Component, types, useProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class FollowerSubtypeDialog extends Component {
    static components = { Dialog };
    static template = "mail.FollowerSubtypeDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.onFollowerChanged = useProps.static(
            "onFollowerChanged",
            onFollowerChangedType(this.store)
        );
        this.close = useProps.static("close", types.function([types.instanceOf(MouseEvent)]));
        this.follower = propComputed("follower", types.instanceOf(this.store["mail.followers"]));
        this.subtypes = asyncComputed(
            async () => {
                const { store_data, subtype_ids } = await rpc("/mail/read_subscription_data", {
                    follower_id: this.follower().id,
                });
                this.store.insert(store_data);
                return subtype_ids.map((id) => this.store["mail.message.subtype"].get(id));
            },
            { initial: [] }
        );
    }

    /**
     * @param {Event} ev
     * @param {{ followerAtRender: import("models").Follower, subtype: SubtypeData }} param1
     */
    onChangeCheckbox(ev, { followerAtRender, subtype }) {
        if (ev.target.checked) {
            followerAtRender.subtype_ids.add(subtype);
        } else {
            followerAtRender.subtype_ids.delete(subtype);
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ followerAtRender: import("models").Follower }} param1
     */
    async onClickApply(ev, { followerAtRender }) {
        const thread = followerAtRender.thread;
        const selectedSubtypes = this.subtypes().filter((s) => s.in(followerAtRender.subtype_ids));
        if (selectedSubtypes.length === 0) {
            await followerAtRender.remove();
        } else {
            await this.env.services.orm.call(
                followerAtRender.thread.model,
                "message_subscribe",
                [[followerAtRender.thread.id]],
                {
                    partner_ids: [followerAtRender.partner_id.id],
                    subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                }
            );
            if (this.store.mt_comment.notIn(selectedSubtypes)) {
                followerAtRender.removeRecipient();
            }
            this.env.services.notification.add(_t("Notification preferences updated."), {
                type: "success",
            });
        }
        this.onFollowerChanged({ thread });
        this.close();
    }

    get title() {
        return _t("Notification Preferences");
    }
}
