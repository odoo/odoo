import { MediaWebsitePlugin } from "@html_builder/core/media_website_plugin";
import { registry } from "@web/core/registry";

export class MediaWebsiteTranslationPlugin extends MediaWebsitePlugin {
    static id = "media_website";

    setup() {
        this.popover = this.services.popover;
        this.removeCurrentTooltip = () => {};
    }
}

registry
    .category("translation-plugins")
    .add(MediaWebsiteTranslationPlugin.id, MediaWebsiteTranslationPlugin);
