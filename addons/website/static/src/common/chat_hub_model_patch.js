import { ChatHub } from "@mail/core/common/chat_hub_model";
import { toRaw } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(ChatHub, {
    new(...args) {
        const record = super.new(...args);
        record.onWindowMessage = (...args) => record._onWindowMessage(...args);
        window.addEventListener("message", toRaw(record.onWindowMessage));
        return record;
    },
});

patch(ChatHub.prototype, {
    delete(...args) {
        window.removeEventListener("message", toRaw(this.onWindowMessage));
        super.delete(...args);
    },
    _onWindowMessage({ data }) {
        switch (data) {
            case "WEBSITE_BUILDER:ON": {
                this.store.websiteBuilder.on = true;
                break;
            }
            case "WEBSITE_BUILDER:OFF": {
                this.store.websiteBuilder.on = false;
                break;
            }
            case "WEBSITE_BUILDER:EDITING:ON": {
                this.store.websiteBuilder.editing = true;
                break;
            }
            case "WEBSITE_BUILDER:EDITING:OFF": {
                this.store.websiteBuilder.editing = false;
                break;
            }
            case "WEBSITE_BUILDER:ASK_ON?": {
                this.store.websiteBuilder?.iframeWindow.postMessage("WEBSITE_BUILDER:ON");
                this.store.websiteBuilder?.iframeWindow.postMessage(
                    this.store.websiteBuilder.isEditing
                        ? "WEBSITE_BUILDER:EDITING:ON"
                        : "WEBSITE_BUILDER:EDITING:OFF"
                );
                break;
            }
        }
    },
    get show() {
        if (!this.store.websiteBuilder?.on) {
            return super.show;
        }
        if (Boolean(this.store.embedLivechat) === Boolean(this.store.websiteBuilder?.editing)) {
            return false;
        }
        return super.show;
    },
});
