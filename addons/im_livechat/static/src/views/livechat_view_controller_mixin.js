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
                const thread = await this.store.Thread.getOrFetch({
                    model: "discuss.channel",
                    id: record.resId,
                });
                if (thread) {
                    return thread.open();
                }
            }
            return super.openRecord(record);
        }
    };
