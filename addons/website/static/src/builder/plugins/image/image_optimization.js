import { Plugin } from "@html_editor/plugin";
import { loadImage } from "@html_editor/utils/image_processing";
import { registry } from "@web/core/registry";

export class ImageOptimization extends Plugin {
    static id = "imageOptimization";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_will_save_handlers: this.addImageWidthAndHeight.bind(this),
    };

    async addImageWidthAndHeight(_, editingEl) {
        await Promise.all(
            Object.values(editingEl ?? {})
                .flat()
                .map((node) => [...node.querySelectorAll("img.img-fluid")])
                .flat()
                .map(this.addWidthAndHeight)
        );
    }

    async addWidthAndHeight(imageEl) {
        const src = imageEl.getAttribute("src");
        if (!src) {
            return;
        }
        const image = await loadImage(src);
        if (image.width && image.height) {
            imageEl.setAttribute("width", image.width);
            imageEl.setAttribute("height", image.height);
        }
    }
}

registry.category("website-plugins").add(ImageOptimization.id, ImageOptimization);
