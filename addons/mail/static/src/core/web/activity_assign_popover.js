import { propSignal, propStatic, usePropsPlus } from "@mail/utils/common/hooks";

import { imageUrl } from "@web/core/utils/urls";
import { Component, signal, t } from "@odoo/owl";
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
        this.props = usePropsPlus({
            activity: propSignal(t.instanceOf(this.store["mail.activity"])),
            close: propStatic(t.function([t.instanceOf(MouseEvent)]).optional()),
            hasHeader: propStatic(t.boolean().optional(false)),
            onActivityChanged: propStatic(t.function([t.instanceOf(this.store["mail.thread"])])),
        });
        this.userId = signal(this.props.activity().user_id?.id || false);
        this.userName = signal(this.props.activity().user_id?.name || "");
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
        const thread = this.props.activity().thread;
        this.disableAssignButton.set(true);
        try {
            await this.orm.write("mail.activity", [this.props.activity().id], {
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
