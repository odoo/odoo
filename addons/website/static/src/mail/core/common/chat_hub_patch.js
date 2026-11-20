import { useOnChange } from "@odoo/owl";
import { ChatHub } from "@mail/core/common/chat_hub";
import { patch } from "@web/core/utils/patch";

patch(ChatHub.prototype, {
    setup() {
        super.setup(...arguments);
        useOnChange(
            () => [this.isWebsiteEdition],
            () => {
                this.chatHub.recomputeBubbleStart++;
                if (!this.position.isDragging) {
                    this.resetPosition(); // to take into account new bubble offset
                }
            }
        );
    },
    get isWebsiteEdition() {
        return this.env.services.website?.context.edition;
    },
});
