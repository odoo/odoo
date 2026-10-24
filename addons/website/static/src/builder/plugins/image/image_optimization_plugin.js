import { Plugin } from "@html_editor/plugin";
import { loadImage } from "@html_editor/utils/image_processing";
import { registry } from "@web/core/registry";

function removeImgDimensionStyles(editable) {
    // html_editor converts image dimensions to style attributes. We remove them
    // here to prevent them from being stored at save time.
    for (const imgEl of editable.querySelectorAll("img[data-img-dimensions]")) {
        imgEl.style.removeProperty("width");
        imgEl.style.removeProperty("height");
    }
}

export class ImageOptimizationPlugin extends Plugin {
    static id = "imageOptimization";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_editor_started_handlers: () => removeImgDimensionStyles(this.editable),
        on_image_saved_handlers: async ({ imageEl }) => {
            if (!imageEl.classList.contains("img-fluid")) {
                return;
            }
            const { naturalHeight, naturalWidth } = await loadImage(imageEl.src);

            if (naturalWidth && naturalHeight) {
                imageEl.dataset.imgDimensions = `${imageEl.getAttribute(
                    "src"
                )} ${naturalWidth} ${naturalHeight}`;
            }
        },
    };
}

export class ImageOptimizationTranslationPlugin extends Plugin {
    static id = "imageOptimizationTranslation";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_editor_started_handlers: () => removeImgDimensionStyles(this.editable),
    };
}

registry.category("website-plugins").add(ImageOptimizationPlugin.id, ImageOptimizationPlugin);
registry
    .category("translation-plugins")
    .add(ImageOptimizationTranslationPlugin.id, ImageOptimizationTranslationPlugin);
