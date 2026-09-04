import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { getImageSrc } from "@html_editor/utils/image";
import { loadImage } from "@html_editor/utils/image_processing";

export class ImagePlugin extends Plugin {
    static id = "image";
    static dependencies = ["measurementSnapshot"];
    resources = {
        on_load_reference_content_handlers: () => this.loadImages(this.config.reference),
    };

    /**
     * Return promises for every image to control when they have their final
     * rendered dimensions.
     * Background images do not influence their content dimensions so they don't
     * have to be waited for.
     */
    loadImages(root) {
        const promises = [];
        for (const img of root.querySelectorAll('img[src]:not([src=""])')) {
            const src = getImageSrc(img);
            if (src) {
                promises.push(loadImage(src, img));
            }
        }
        return Promise.allSettled(promises);
    }

    // TODO EGGMAIL:
    // case study: background color + color filter => should apply the same logic as a normal
    // filter? => if the logic is to create a new attachment. If it uses browser rendering
    // capabilities, then it won't work
    // issue: the filter is currently an external div with position: absolute
}

registry.category("mail-html-conversion-core-plugins").add(ImagePlugin.id, ImagePlugin);
