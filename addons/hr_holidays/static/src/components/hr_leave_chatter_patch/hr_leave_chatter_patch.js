import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.applyConditionalAttachmentVisibility();
    },

     async applyConditionalAttachmentVisibility() {
        try {
            if (this.props.threadModel === "hr.leave" && this.props.threadId) {
                const record = await this.orm.read(
                    "hr.leave",
                    [this.props.threadId],
                    ["attachment_is_visible"]
                );
                const isVisible = record?.[0]?.attachment_is_visible;
                if (!isVisible) {
                    if (this.state.thread) {
                        this.state.thread.attachments = [];
                    }
                }
            }
        } catch (error) {
            console.warn("Failed to check attachment visibility:", error);
        }
    },
});
