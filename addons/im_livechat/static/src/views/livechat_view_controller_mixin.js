import { useService } from "@web/core/utils/hooks";

export const LivechatViewControllerMixin = (ViewController) =>
    class extends ViewController {
        setup() {
            super.setup(...arguments);
            this.store = useService("mail.store");
            this.ui = useService("ui");
        }

        async openRecord(record) {
            if (this.ui.isSmall) {
                const channel = await this.store["discuss.channel"].getOrFetch(record.resId);
                channel?.open();
            }
            return super.openRecord(record);
        }
    };
