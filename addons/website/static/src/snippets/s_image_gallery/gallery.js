import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";
import { Interaction } from "@web/public/interaction";

export class Gallery extends Interaction {
    static selector = ".s_image_gallery.o_image_popup";
    dynamicContent = {
        img: {
            "t-on-click": this.onClickImg,
        },
    };

    setup() {
        this.originalSources = [...this.el.querySelectorAll("img")].map((img) =>
            img.getAttribute("src")
        );
        this.carouselEl = this.el.querySelector(".carousel");
        this.carouselInstance =
            this.carouselEl && window.Carousel.getOrCreateInstance(this.carouselEl);
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

        // Pause carousel autoplay while the lightbox is active
        if (this.carouselEl) {
            this.carouselRideValue = this.carouselInstance._config.ride;
            this.carouselInstance.pause();
            this.carouselInstance._config.ride = false;
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

        this.hasMultipleImages = imageEls.length > 1;
        this.modalEl = this.renderAt("website.image_mirror.lightbox", {
            images: imageEls,
            index: currentImageIndex,
            dim: dimensions,
            interval: milliseconds || 0,
            ride: !milliseconds ? "false" : "carousel",
            id: uniqueId("slideshow_"),
            shouldShowControls: this.hasMultipleImages,
        })[0];
        this.insert(this.modalEl, document.body);
        new Modal(this.modalEl, { keyboard: true }).show();

        // Restore carousel autoplay when closing the lightbox modal
        if (this.carouselEl) {
            this.addListener(this.modalEl, "hidden.bs.modal", () => {
                // Restore the carousel's original auto-cycling state
                this.carouselInstance._config.ride = this.carouselRideValue;
                this.carouselInstance._maybeEnableCycle();
            });
        }
    }
}

registry.category("public.interactions").add("website.gallery", Gallery);
