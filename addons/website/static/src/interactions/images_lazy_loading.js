import { registry } from "@web/core/registry";
import { Interaction } from "@website/core/interaction";
import { onceAllImagesLoaded } from "@website/interactions/utils";
/**
 * The websites, by default, use image lazy loading via the loading="lazy"
 * attribute on <img> elements. However, this does not work great on all
 * browsers. This widget fixes the behaviors with as less code as possible.
 */
export class ImagesLazyLoading extends Interaction {
    static selector = "#wrapwrap";
    static dynamicContent = {
    };

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
        const imgEls = this.el.querySelectorAll("img[loading='lazy']");
        for (const imgEl of imgEls) {
            this.updateImgMinHeight(imgEl);
            this.waitFor(() => onceAllImagesLoaded(imgEl)).then(() => {
                this.restoreImage(imgEl);
            });
        }
    }
    destroy() {
        const imgEls = this.el.querySelectorAll("img[data-lazy-loading-initial-min-height]");
        for (const imgEl of imgEls) {
            this.restoreImage(imgEl);
        }
    }
    /**
     * @param {HTMLImageElement} imgEl
     */
    restoreImage(imgEl) {
        this.updateImgMinHeight(imgEl, true);
    }
    /**
     * Updates the image element style with the corresponding min-height.
     * If the editor is enabled, it deactivates the observer during the CSS
     * update.
     *
     * @param {HTMLElement} imgEl - The image element to update the minimum
     *        height of.
     * @param {boolean} [reset=false] - Whether to remove the minimum height
     *        and restore the initial value.
     */
    updateImgMinHeight(imgEl, reset = false) {
        // TODO Editor behavior.
        /*
        if (this.options.wysiwyg) {
            this.options.wysiwyg.odooEditor.observerUnactive("updateImgMinHeight"");
        }
        */
        if (reset) {
            imgEl.style.minHeight = imgEl.dataset.lazyLoadingInitialMinHeight;
            delete imgEl.dataset.lazyLoadingInitialMinHeight;
        } else {
            // Write initial min-height on the dataset, so that it can also
            // be properly restored on widget destroy.
            imgEl.dataset.lazyLoadingInitialMinHeight = imgEl.style.minHeight;
            imgEl.style.minHeight = "1px";
        }
        // TODO Editor behavior.
        /*
        if (this.options.wysiwyg) {
            this.options.wysiwyg.odooEditor.observerActive("updateImgMinHeight");
        }
        */
    }
}

registry.category("website.active_elements").add("website.images_lazy_loading", ImagesLazyLoading);
