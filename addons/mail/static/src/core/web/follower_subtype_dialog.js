import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} SubtypeData
 * @property {boolean} followed
 * @property {number} id
 * @property {string} name
 */

/**
 * @typedef {Object} Props
 * @property {function} close
 * @property {import("models").Follower} follower
 * @property {function} onFollowerChanged
 * @extends {Component<Props, Env>}
 */
export class FollowerSubtypeDialog extends Component {
    static components = { Dialog };
    static props = ["close", "follower?", "thread?", "onFollowerChanged"];
    static template = "mail.FollowerSubtypeDialog";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.state = useState({
            /** @type {SubtypeData[]} */
            subtypes: [],
        });
        onWillStart(async () => {
            this.state.subtypes = await rpc("/mail/read_subscription_data", {
                follower_id: this.props.follower?.id,
                thread_model: this.props.thread?.model,
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
        if (this.props.follower) {
            await this.updateFollowerSubscriptions(selectedSubtypes);
            this.env.services.notification.add(
                _t("The subscription preferences were successfully applied."),
                { type: "success" }
            );
            this.props.close();
        }
        if (this.props.thread) {
            await this.updateThreadDefaultSubscriptions(selectedSubtypes);
        }
    }

    async onClickApplyAll() {
        const dialogProps = {
            title: _t("Are you sure you want to change the default subscription?"),
            body: _t(
                "This selection will be applied to all new records of this user having the same model type."
            ),
            confirm: async () => {
                const selectedSubtypes = this.state.subtypes.filter((s) => s.followed);
                await this.updateFollowerSubscriptions(selectedSubtypes);
                await this.env.services.orm.call(
                    "mail.message.subtype.settings",
                    "set_mail_message_subtype_settings",
                    [[]],
                    {
                        partner_id: this.props.follower.partner.id,
                        thread_model: this.props.follower.thread.model,
                        subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                    }
                );
                this.env.services.notification.add(
                    _t("The subscription preferences were successfully applied."),
                    { type: "success" }
                );
                this.props.close();
            },
            cancel: () => {},
        };
        return this.env.services.dialog.add(ConfirmationDialog, dialogProps);
    }

    async updateThreadDefaultSubscriptions(selectedSubtypes) {
        const dialogProps = {
            title: _t("Are you sure you want to change the default subscription?"),
            body: _t(
                "This selection will be applied to all new followers. Existing ones won't be affected by the changes."
            ),
            confirm: async () => {
                await rpc("/mail/thread/default_subscribe", {
                    thread_model: this.props.thread.model,
                    subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                });
                this.env.services.notification.add(
                    _t("The subscription preferences were successfully applied."),
                    { type: "success" }
                );
                this.props.close();
            },
            cancel: () => {},
        };
        return this.env.services.dialog.add(ConfirmationDialog, dialogProps);
    }

    async updateFollowerSubscriptions(selectedSubtypes) {
        const thread = this.props.follower.thread;
        if (selectedSubtypes.length === 0) {
            await this.props.follower.remove();
        } else {
            await this.env.services.orm.call(
                this.props.follower.thread.model,
                "message_subscribe",
                [[this.props.follower.thread.id]],
                {
                    partner_ids: [this.props.follower.partner.id],
                    subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                }
            );
            if (!selectedSubtypes.some((subtype) => subtype.id === this.store.mt_comment_id)) {
                this.props.follower.removeRecipient();
            }
        }
        this.props.onFollowerChanged(thread);
    }

    get title() {
        if (this.props.follower) {
            return _t("Edit Subscription of %(name)s", { name: this.props.follower.partner.name });
        }
        return _t("Edit Default Subscription");
    }
}
