import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useOnChange } from "@mail/utils/common/hooks";

patch(Discuss.prototype, {
    setup() {
        super.setup();
        this.title = useService("title");
        useOnChange(
            () => [this.thread?.channel?.displayName || this.thread?.displayName],
            (threadName) => {
                if (threadName) {
                    this.title.setParts({ action: threadName });
                }
            }
        );
    },
});
