/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";

export class DiscussChannelListController extends ListController {
    openRecord(record) {
        if (!record.data.is_member) {
            return super.openRecord(record);
        }
        this.actionService.doAction("mail.action_discuss", {
            additionalContext: {
                active_id: record.resId,
            },
            name: _t("Discuss"),
        });
    }
}
