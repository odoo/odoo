import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { onceAllImagesLoaded } from "@website/utils/images";
/**
 * The websites, by default, use image lazy loading via the loading="lazy"
 * attribute on <img> elements. However, this does not work great on all
 * browsers. This widget fixes the behaviors with as less code as possible.
 */
export class ImageLazyLoading extends Interaction {
    static selector = "#wrapwrap img[loading='lazy']";

    setup() {
        // For each image on the page, force a 1px min-height so that Chrome
        // understands the image exists on different zoom sizes of the browser.
        // Indeed, without this, on a 90% zoom, some images were never loaded.
        // Once the image has been loaded, the 1px min-height is removed.
        // Note: another possible solution without JS would be this CSS rule:
        // ```
        // [loading="lazy"] {
        //     min-height: 1px;
        // }
        // ```
        // This would solve the problem the same way with a CSS rule with a
        // very small priority (any class setting a min-height would still have
        // priority). However, the min-height would always be forced even once
        // the image is loaded, which could mess with some layouts relying on
        // the image intrinsic min-height.
        this.initialHeight = this.el.style.minHeight;
        this.el.style.minHeight = "1px";
    }

    async willStart() {
        await onceAllImagesLoaded(this.el);
    }

    start() {
        this.restoreImage();
    }

    destroy() {
        this.restoreImage();
    }

    restoreImage() {
        this.el.style.minHeight = this.initialHeight;
    }
}

registry
    .category("public.interactions")
    .add("website.image_lazy_loading", ImageLazyLoading);
