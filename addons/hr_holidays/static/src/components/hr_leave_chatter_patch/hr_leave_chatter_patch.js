import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useService } from "@web/core/utils/hooks";


patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");

        this.state.hasAttachmentPreview = this.props.hasAttachmentPreview ?? true;
        this.state.isAttachmentBoxOpened = this.props.isAttachmentBoxOpened ?? true;
        this.state.isAttachmentBoxVisibleInitially = this.props.isAttachmentBoxVisibleInitially ?? true;

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
                    this.state.hasAttachmentPreview = false;
                    this.state.isAttachmentBoxOpened = false;
                    this.state.isAttachmentBoxVisibleInitially = false;
                    if (this.state.thread) {
                        this.state.thread.attachments = []; // Clear attachments
                    }
                }
            }
        } catch (error) {
            console.warn("Failed to check attachment visibility:", error);
        }
    },
});
