import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export const LivechatViewControllerMixin = (ViewController) =>
    class extends ViewController {
        setup() {
            super.setup(...arguments);
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
            const thread = await this.store.Thread.getOrFetch({
                model: "discuss.channel",
                id: record.resId,
            });
            if (thread) {
                return thread.open();
            }
            return super.openRecord(record);
        }
    };
