/* @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} SubtypeData
 * @property {boolean} followed
 * @property {number} id
 * @property {string} name
 */

/**
 * @typedef {Object} Props
 * @property {function} close
 * @property {import("@mail/new/core/follower_model").Follower} follower
 * @property {function} onFollowerChanged
 * @extends {Component<Props, Env>}
 */
export class FollowerSubtypeDialog extends Component {
    static components = { Dialog };
    static props = ["close", "follower", "onFollowerChanged"];
    static template = "mail.FollowerSubtypeDialog";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            /** @type {SubtypeData[]} */
            subtypes: [],
        });
        onWillStart(async () => {
            this.state.subtypes = await this.rpc("/mail/read_subscription_data", {
                follower_id: this.props.follower.id,
            });
        });
    }

    /**
     * @param {Event} ev
     * @param {SubtypeData} subtype
     */
    onChangeCheckbox(ev, subtype) {
        subtype.followed = ev.target.checked;
    }

    async onClickApply() {
        const selectedSubtypes = this.state.subtypes.filter((s) => s.followed);
        if (selectedSubtypes.length === 0) {
            await this.env.services["mail.thread"].removeFollower(this.props.follower);
        } else {
            await this.env.services.orm.call(
                this.props.follower.followedThread.resModel,
                "message_subscribe",
                [[this.props.follower.followedThread.resId]],
                {
                    partner_ids: [this.props.follower.partner.id],
                    subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                }
            );
            this.env.services.notification.add(
                _t("The subscription preferences were successfully applied."),
                { type: "success" }
            );
        }
        this.props.onFollowerChanged();
        this.props.close();
    }

    get title() {
        return sprintf(_t("Edit Subscription of %(name)s"), {
            name: this.props.follower.partner.name,
        });
    }
}
