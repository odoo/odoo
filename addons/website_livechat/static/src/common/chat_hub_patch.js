import { ChatHub } from "@mail/core/common/chat_hub";
import { onWillDestroy, useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(ChatHub.prototype, {
    setup() {
        super.setup(...arguments);
        this.onWindowMessage = this.onWindowMessage.bind(this);
        onWillDestroy(() => {
            window.removeEventListener("message", this.onWindowMessage);
        });
        window.addEventListener("message", this.onWindowMessage);
        if (this.env.embedLivechat) {
            parent?.postMessage("WEBSITE_BUILDER:ASK_ON?");
        } else {
            useEffect(
                (websiteBuilderOn, editing, iframeWindow) => {
                    if (!this.store.websiteBuilder || this.env.embedLivechat) {
                        return;
                    }
                    iframeWindow?.postMessage(
                        websiteBuilderOn ? "WEBSITE_BUILDER:ON" : "WEBSITE_BUILDER:OFF"
                    );
                    if (websiteBuilderOn) {
                        iframeWindow?.postMessage(
                            editing ? "WEBSITE_BUILDER:EDITING:ON" : "WEBSITE_BUILDER:EDITING:OFF"
                        );
                    }
                },
                () => [
                    this.store.websiteBuilder?.on,
                    this.store.websiteBuilder?.editing,
                    this.store.websiteBuilder?.iframeWindow,
                ]
            );
        }
    },
    onWindowMessage({ data }) {
        switch (data) {
            case "WEBSITE_BUILDER:ON": {
                if (!this.env.embedLivechat) {
                    return;
                }
                Object.assign(this.store.websiteBuilder, { on: true });
                break;
            }
            case "WEBSITE_BUILDER:OFF": {
                if (!this.env.embedLivechat) {
                    return;
                }
                Object.assign(this.store.websiteBuilder, { on: false });
                break;
            }
            case "WEBSITE_BUILDER:EDITING:ON": {
                if (!this.env.embedLivechat) {
                    return;
                }
                Object.assign(this.store.websiteBuilder, { editing: true });
                break;
            }
            case "WEBSITE_BUILDER:EDITING:OFF": {
                if (!this.env.embedLivechat) {
                    return;
                }
                Object.assign(this.store.websiteBuilder, { editing: false });
                break;
            }
            case "WEBSITE_BUILDER:ASK_ON?": {
                if (this.env.embedLivechat) {
                    return;
                }
                if (!this.env.embedLivechat && this.store.websiteBuilder) {
                    this.store.websiteBuilder.iframeWindow.postMessage("WEBSITE_BUILDER:ON");
                    this.store.websiteBuilder.iframeWindow.postMessage(
                        this.store.websiteBuilder.isEditing
                            ? "WEBSITE_BUILDER:EDITING:ON"
                            : "WEBSITE_BUILDER:EDITING:OFF"
                    );
                }
                break;
            }
        }
    },
    get show() {
        if (!this.store.websiteBuilder?.on) {
            return super.show;
        }
        if (Boolean(this.env.embedLivechat) === Boolean(this.store.websiteBuilder?.editing)) {
            return false;
        }
        return super.show;
    },
});
