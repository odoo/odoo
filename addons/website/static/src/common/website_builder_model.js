import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class WebsiteBuilder extends Record {
    on = fields.Attr(false, {
        /** @this {import("models").WebsiteBuilder} */
        onUpdate() {
            this.onUpdate();
        },
    });
    editing = fields.Attr(false, {
        /** @this {import("models").WebsiteBuilder} */
        onUpdate() {
            this.onUpdate();
        },
    });
    iframeWindow = fields.Attr(undefined, {
        /** @this {import("models").WebsiteBuilder} */
        onUpdate() {
            this.onUpdate();
        },
    });
    onUpdate() {
        this.iframeWindow?.postMessage(this.on ? "WEBSITE_BUILDER:ON" : "WEBSITE_BUILDER:OFF");
        if (this.on) {
            this.iframeWindow?.postMessage(
                this.editing ? "WEBSITE_BUILDER:EDITING:ON" : "WEBSITE_BUILDER:EDITING:OFF"
            );
        }
    }
}

WebsiteBuilder.register();
