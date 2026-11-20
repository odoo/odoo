import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class ImagePlugin extends Plugin {
    static id = "image";
    static dependencies = ["measurementSnapshot"];
    resources = {
        on_load_reference_content_handlers: () => this.loadImages(this.config.reference),
    };

    loadImage(img) {
        return new Promise((resolve, reject) => {
            if (img.complete) {
                resolve(img);
            }
            img.addEventListener("load", () => resolve(img), { once: true });
            img.addEventListener("error", reject, { once: true });
        });
    }

    /**
     * Return promises for every image to control when they have their final
     * rendered dimensions.
     * Background images do not influence their content dimensions so they don't
     * have to be waited for.
     * TODO EGGMAIL: load background images as well and enforce a background color
     * according to the vibe of the image, to ensure contrast for mail clients
     * that don't support them
     */
    loadImages(root) {
        const promises = [];
        for (const img of root.querySelectorAll('img[src]:not([src=""])')) {
            promises.push(this.loadImage(img));
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
