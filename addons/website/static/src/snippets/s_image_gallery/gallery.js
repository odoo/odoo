import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";
import { BaseLightbox } from "../../interactions/base_lightbox_popup";

export class Gallery extends BaseLightbox {
    static selector = ".s_image_gallery.o_image_popup";
    dynamicContent = {
        img: {
            "t-on-click": this.onClickImg,
        },
    };

    setup() {
        super.setup();
        this.originalSources = [...this.el.querySelectorAll("img")].map((img) =>
            img.getAttribute("src")
        );
    }

    /**
     * Called when an image is clicked. Opens a dialog to browse all the images
     * with a bigger size.
     *
     * @param {Event} ev
     */
    onClickImg(ev) {
        const clickedEl = ev.currentTarget;
        if (clickedEl.matches("a > img")) {
            return;
        }

        let imageEls = this.el.querySelectorAll("img");
        const currentImageEl = clickedEl.closest("img");
        const currentImageIndex = [...imageEls].indexOf(currentImageEl);
        // We need to reset the images to their original source because it might
        // have been changed by a mouse event (e.g. "hover effect" animation).
        imageEls = [...imageEls].map((el, i) => {
            const cloneEl = el.cloneNode(true);
            cloneEl.src = this.originalSources[i];
            return cloneEl;
        });

        const size = 0.8;
        const dimensions = {
            min_width: Math.round(window.innerWidth * size * 0.9),
            min_height: Math.round(window.innerHeight * size),
            max_width: Math.round(window.innerWidth * size * 0.9),
            max_height: Math.round(window.innerHeight * size),
            width: Math.round(window.innerWidth * size * 0.9),
            height: Math.round(window.innerHeight * size),
        };

        const milliseconds = this.el.dataset.interval || false;
        const lightboxTemplate =
            this.el.dataset.vcss === "002"
                ? "website.image_mirror.lightbox"
                : "website.gallery.slideshow.lightbox";
        this.hasMultipleImages = imageEls.length > 1;
        this.openLightbox(lightboxTemplate, {
            images: imageEls,
            index: currentImageIndex,
            dim: dimensions,
            interval: milliseconds || 0,
            ride: !milliseconds ? "false" : "carousel",
            id: uniqueId("slideshow_"),
            shouldShowControls: this.hasMultipleImages,
        });
    }
}

registry.category("public.interactions").add("website.gallery", Gallery);
