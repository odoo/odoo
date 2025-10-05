
import { ChatHub } from "@mail/core/common/chat_hub";
import { patch } from "@web/core/utils/patch";

patch(ChatHub.prototype, {
    setup() {
        super.setup(...arguments);
        const whatsAppSnippet = document.querySelector(".s_whatsapp_container");
        if (whatsAppSnippet && !this._isWhatsAppActive) {
            this.position.bottom = `${whatsAppSnippet.getBoundingClientRect().height + 20}px`;
            this._isWhatsAppActive = true;
        }
    },
  
});
