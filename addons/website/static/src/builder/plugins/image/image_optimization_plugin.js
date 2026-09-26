import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ImageOptimizationPlugin extends Plugin {
    static id = "imageOptimization";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_editor_started_handlers: () => {
            for (const imgEl of this.editable.querySelectorAll("img[data-img-dimensions]")) {
                imgEl.style.removeProperty("width");
                imgEl.style.removeProperty("height");
            }
        },
        on_image_saved_handlers: ({ imageEl }) => {
            if (imageEl.naturalWidth && imageEl.naturalHeight) {
                imageEl.dataset.imgDimensions = `${imageEl.getAttribute("src")} ${
                    imageEl.naturalWidth
                } ${imageEl.naturalHeight}`;
            }
        },
    };
}

registry.category("website-plugins").add(ImageOptimizationPlugin.id, ImageOptimizationPlugin);
