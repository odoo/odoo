import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { useOnChange } from "@mail/utils/common/hooks";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        useOnChange(
            () => [this.thread()],
            (thread) => {
                this.applyConditionalAttachmentVisibility(thread);
            }
        );
    },

    async applyConditionalAttachmentVisibility(thread) {
        try {
            if (thread?.model === "hr.leave" && thread?.id) {
                const record = await this.orm.read(
                    "hr.leave",
                    [thread.id],
                    ["attachment_is_visible"]
                );
                const isVisible = record?.[0]?.attachment_is_visible;
                if (!isVisible) {
                    thread.attachments = [];
                }
            }
        } catch (error) {
            console.warn("Failed to check attachment visibility:", error);
        }
    },
});
