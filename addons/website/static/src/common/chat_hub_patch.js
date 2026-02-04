import { useLayoutEffect } from "@web/owl2/utils";
import { ChatHub } from "@mail/core/common/chat_hub";
import { patch } from "@web/core/utils/patch";

patch(ChatHub.prototype, {
    setup() {
        super.setup(...arguments);
        useLayoutEffect(
            () => {
                this.chatHub.recomputeBubbleStart++;
                if (!this.position.isDragging) {
                    this.resetPosition(); // to take into account new bubble offset
                }
            },
            () => [this.isWebsiteEdition]
        );
    },
    get isWebsiteEdition() {
        return this.env.services.website?.context.edition;
    },
});
