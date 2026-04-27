import { useState } from "@odoo/owl";

import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

export class WhatsappChannelListController extends ListController {
    setup() {
        super.setup(...arguments);
        this.store = useState(useService("mail.store"));
    }

    async openRecord(record) {
        const thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: record.resId,
        });
        if (thread) {
            return thread.open();
        }
        return super.openRecord(record);
    }
}
