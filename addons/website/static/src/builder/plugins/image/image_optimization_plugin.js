import { Plugin } from "@html_editor/plugin";
import { loadImage } from "@html_editor/utils/image_processing";
import { registry } from "@web/core/registry";

export class ImageOptimizationPlugin extends Plugin {
    static id = "imageOptimization";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_editor_started_handlers: () => {
            // Remove width/height from img elements to prevent them from being
            // stored at save time.
            for (const imgEl of this.editable.querySelectorAll("img[data-img-dimensions]")) {
                imgEl.removeAttribute("width");
                imgEl.removeAttribute("height");
            }
        },
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

registry.category("website-plugins").add(ImageOptimizationPlugin.id, ImageOptimizationPlugin);
