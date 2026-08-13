import { rpc } from "@web/core/network/rpc";
import { Component, markup, onWillStart, signal, types, useProps } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class FollowerSubtypeDialog extends Component {
    static components = { Dialog };
    static template = "mail.FollowerSubtypeDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            close: types.function([types.instanceOf(MouseEvent)]),
            follower: types.instanceOf(this.store["mail.followers"]),
            onFollowerChanged: types.function([]),
        });
        this.subtypes = signal(null, {
            type: types.array(types.instanceOf(this.store["mail.message.subtype"])),
        });
        onWillStart(async () => {
            const { store_data, subtype_ids, parent_id, parent_model } = await rpc(
                "/mail/read_subscription_data",
                { follower_id: this.props.follower.id }
            );
            this.store.insert(store_data);
            this.subtypes.set(subtype_ids.map((id) => this.store["mail.message.subtype"].get(id)));
            this.parentRecord = this.store["mail.thread"].get({
                id: parent_id,
                model: parent_model,
            });
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

    async onClickUpdateAll() {
        this.store.env.services.dialog.add(ConfirmationDialog, {
            body: _t(
                'Are you sure you want to mass-update notifications preferences of all existing records of the %(parent_model_name)s "%(parent_record_name)s"?',
                {
                    parent_model_name: this.parentRecord.modelName.toLowerCase(),
                    parent_record_name: this.parentRecord.display_name,
                }
            ),
            confirmLabel: _t("Yes, Update All"),
            confirm: async () => {
                await this.updateSubscription({ updateAll: true });
            },
            cancel: () => {},
        });
    }

    async updateSubscription({ updateAll = false } = {}) {
        const thread = this.props.follower.thread;
        const selectedSubtypes = this.subtypes().filter((s) =>
            s.in(this.props.follower.subtype_ids)
        );
        if (updateAll) {
            await this.env.services.orm.call(
                thread.model,
                "message_update_siblings_subscription",
                [[thread.id]],
                {
                    partner_ids: [this.props.follower.partner_id.id],
                    subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                }
            );
        } else {
            if (selectedSubtypes.length === 0) {
                await this.props.follower.remove();
            } else {
                await this.env.services.orm.call(thread.model, "message_subscribe", [[thread.id]], {
                    partner_ids: [this.props.follower.partner_id.id],
                    subtype_ids: selectedSubtypes.map((subtype) => subtype.id),
                });
            }
        }
        if (this.store.mt_comment.notIn(selectedSubtypes)) {
            this.props.follower.removeRecipient();
        }
        this.env.services.notification.add(_t("Notification preferences updated."), {
            type: "success",
        });
        this.props.onFollowerChanged(thread);
        this.props.close();
    }

    get title() {
        return _t("Notification Preferences");
    }

    get isParentModel() {
        return this.subtypes().some((subtype) => subtype.parent_id);
    }

    get childRecordsHint() {
        return _t(
            "This sets default notifications for all future records under this %(model_name)s.",
            { model_name: this.props.follower.thread.modelName.toLowerCase() }
        );
    }

    get parentRecordHint() {
        const record = this.parentRecord;
        const parentRecordLink = markup`<a data-oe-model="${record.model}" href="/odoo/${record.model}/${record.id}">${record.display_name}</a>`;
        return _t(
            "💡 You can set default notifications for all future records in the notification preferences of the %(parent_model_name)s %(parent_record_name)s.",
            {
                parent_model_name: record.modelName.toLowerCase(),
                parent_record_name: parentRecordLink,
            }
        );
    }

    /** @param {MouseEvent} ev */
    onClickParentRecordLink(ev) {
        if (!ev.target.closest(`a[data-oe-model="${this.parentRecord.model}"]`)) {
            return;
        }
        ev.preventDefault();
        this.parentRecord.open();
    }
}
