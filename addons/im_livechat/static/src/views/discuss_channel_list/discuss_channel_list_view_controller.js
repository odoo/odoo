/* @odoo-module */

import { createLocalId } from "@mail/utils/common/misc";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

export class DiscussChannelListController extends ListController {
    setup() {
        super.setup(...arguments);
        this.threadService = useService("mail.thread");
        this.store = useService("mail.store");
    }

    async openRecord(record) {
        if (!record.data.is_member) {
            return super.openRecord(record);
        }
        const channel =
            this.store.threads[createLocalId(record.resModel, record.resId)] ??
            (await this.threadService.fetchChannel(record.resId));
        if (!channel.is_pinned) {
            this.threadService.pin(channel);
        }
        this.threadService.setDiscussThread(channel);
        this.actionService.doAction("mail.action_discuss", {
            name: _t("Discuss"),
        });
    }
}
