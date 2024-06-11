/* @odoo-module */

import { useState } from "@odoo/owl";

import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DiscussChannelListController extends ListController {
    setup() {
        super.setup(...arguments);
        this.threadService = useService("mail.thread");
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
    }

    async openRecord(record) {
        if (!this.ui.isSmall) {
            return this.actionService.doAction("mail.action_discuss", {
                name: _t("Discuss"),
                additionalContext: { active_id: record.resId },
            });
        }
        let thread = this.store.Thread.get({
            model: "discuss.channel",
            id: record.resId,
        });
        if (!thread?.type) {
            thread = await this.threadService.fetchChannel(record.resId);
        }
        if (thread) {
            return this.threadService.open(thread);
        }
        return super.openRecord(record);
    }
}
