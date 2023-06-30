/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";

export class DiscussChannelListController extends ListController {
    setup() {
        super.setup(...arguments);
    }

    async openRecord(record) {
        if (!record.data.is_member) {
            return super.openRecord(record);
        }
        this.actionService.doAction("mail.action_discuss", {
            name: _t("Discuss"),
            additionalContext: { active_id: record.resId },
        });
    }
}
