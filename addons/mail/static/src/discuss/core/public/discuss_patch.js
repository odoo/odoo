import { Discuss } from "@mail/core/public_web/discuss";
import { useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Discuss.prototype, {
    setup() {
        super.setup();
        this.title = useService("title");
        useEffect(
            (threadName) => {
                if (threadName) {
                    this.title.setParts({ action: threadName });
                }
            },
            () => [this.thread?.displayName]
        );
    },
});
