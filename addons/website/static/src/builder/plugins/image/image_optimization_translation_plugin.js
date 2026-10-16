import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ImageOptimizationTranslationPlugin extends Plugin {
    static id = "imageOptimization";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_editor_started_handlers: () => {
            // html_editor converts image dimensions to style attributes. We remove them here
            // to prevent them from being stored at save time.
            for (const imgEl of this.editable.querySelectorAll("img[data-img-dimensions]")) {
                imgEl.style.removeProperty("width");
                imgEl.style.removeProperty("height");
            }
        },
    };
}

registry
    .category("translation-plugins")
    .add(ImageOptimizationTranslationPlugin.id, ImageOptimizationTranslationPlugin);
