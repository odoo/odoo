import { useLayoutEffect } from "@web/owl2/utils";
import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Discuss.prototype, {
    setup() {
        super.setup();
        this.title = useService("title");
        useLayoutEffect(
            (threadName) => {
                if (threadName) {
                    this.title.setParts({ action: threadName });
                }
            },
            () => [this.thread?.channel?.displayName || this.thread?.displayName]
        );
    },
});
