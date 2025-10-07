import { MediaWebsitePlugin } from "@html_builder/core/media_website_plugin";
import { registry } from "@web/core/registry";
import {
    translateDocumentOptionSelector,
    translateImageOptionSelector,
} from "./options/media_translation_plugin";

export class MediaWebsiteTranslationPlugin extends MediaWebsitePlugin {
    static id = "media_website";

    basicMediaSelector = [translateImageOptionSelector, translateDocumentOptionSelector].join(", ");

    /**
     * @override
     * @param {HTMLElement} mediaEl
     * @returns {Boolean}
     */
    isReplaceableMedia(mediaEl) {
        if (mediaEl.matches(translateDocumentOptionSelector)) {
            return true;
        }
        // An element marked `.o_translatable_attribute` means that it went
        // through `findOEditable` and `buildTranslationInfoMap` in the
        // TranslationPlugin. We can rely on that information.
        return mediaEl.classList.contains("o_translatable_attribute");
    }
}

registry
    .category("translation-plugins")
    .add(MediaWebsiteTranslationPlugin.id, MediaWebsiteTranslationPlugin);
