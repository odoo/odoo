import { Chatter } from "@mail/chatter/web_portal_project/chatter";

import { useOnChange, usePlugin } from "@odoo/owl";

import { ORM } from "@web/core/orm_plugin";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.orm = usePlugin(ORM);
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
            // The component was destroyed during the call: rethrow so the AbortError skips the
            // error handling below and reaches the global handler, which silently ignores it.
            if (error.name === "AbortError") {
                throw error;
            }
            console.warn("Failed to check attachment visibility:", error);
        }
    },
});
