import { imageUrl } from "@web/core/utils/urls";
import { Component, props, signal, types } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class ActivityAssignPopover extends Component {
    static template = "mail.ActivityAssignPopover";
    static components = { Many2XAutocomplete };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.orm = useService("orm");
        this.responsibleLabel = _t("Responsible");
        this.props = props(
            {
                activity: types.instanceOf(this.store["mail.activity"].Class),
                close: types.function().optional(),
                hasHeader: types.boolean().optional(),
                onActivityChanged: types.function([
                    types.instanceOf(this.store["mail.thread"].Class),
                ]),
            },
            { hasHeader: false }
        );
        this.userId = signal(this.props.activity.user_id?.id || false);
        this.userName = signal(this.props.activity.user_id?.name || "");
        this.disableAssignButton = signal(false);
    }

    getAvatarUrl(userId) {
        if (!userId) {
            return undefined;
        }
        return (
            this.store["res.users"].get(userId)?.avatarUrl ??
            imageUrl("res.users", userId, "avatar_128")
        );
    }

    getDomain() {
        return [["share", "=", false]];
    }

    onSelect(records) {
        if (!records) {
            this.userId.set(false);
            this.userName.set("");
            return;
        }
        const record = records[0];
        this.userId.set(record?.id || false);
        this.userName.set(record?.display_name || record?.name || "");
    }

    async onClickAssign() {
        if (this.disableAssignButton()) {
            return;
        }
        const { res_id, res_model } = this.props.activity;
        const thread = this.store["mail.thread"].insert({ model: res_model, id: res_id });
        this.disableAssignButton.set(true);
        try {
            await this.orm.write("mail.activity", [this.props.activity.id], {
                user_id: this.userId() || false,
            });
            this.props.onActivityChanged(thread);
            await thread.fetchNewMessages();
        } finally {
            this.disableAssignButton.set(false);
        }
        if (this.props.close) {
            this.props.close();
        }
    }
}
