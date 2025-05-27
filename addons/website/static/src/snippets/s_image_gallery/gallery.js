import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";
import * as masonryUtils from "@web_editor/js/common/masonry_layout_utils";
import wUtils from "@website/js/utils";

export class Gallery extends Interaction {
    static selector = ".s_image_gallery:not(.o_slideshow)";
    dynamicContent = {
        "img": {
            "t-on-click": this.onClickImg,
        },
        "#btn-expand-gallery": {
            "t-on-click": this.expandGallery,
        },
        "#btn-collapse-gallery": {
            "t-on-click": this.collapseGallery,
        },
    };

    setup() {
        this.modalEl = null;
        this.originalSources = [...this.el.querySelectorAll("img")].map(img => img.getAttribute("src"));

        if (this.el.classList.contains("o_masonry")) {
            masonryUtils.observeMasonryLayoutWidthChange(this.el);
        }
    }

    destroy() {
        if (this.el.dataset.expandable === "true") {
            this.collapseGallery({ scrollGalleryIntoView: false });
        }
    }

    /**
     * Called when an image is clicked. Opens a dialog to browse all the images
     * with a bigger size.
     *
     * @param {Event} ev
     */
    onClickImg(ev) {
        const clickedEl = ev.currentTarget;
        if (this.modalEl || clickedEl.matches("a > img")) {
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
        const lightboxTemplate = this.el.dataset.vcss === "002"
            ? "website.gallery.s_image_gallery_mirror.lightbox"
            : "website.gallery.slideshow.lightbox";

        this.modalEl = renderToElement(lightboxTemplate, {
            images: imageEls,
            index: currentImageIndex,
            dim: dimensions,
            interval: milliseconds || 0,
            ride: !milliseconds ? "false" : "carousel",
            id: uniqueId("slideshow_"),
        });

        this.onModalKeydownBound = this.onModalKeydown.bind(this);

        this.modalEl.addEventListener("hidden.bs.modal", () => {
            this.modalEl.classList.add("d-none");
            for (const backdropEl of this.modalEl.querySelectorAll(".modal-backdrop")) {
                backdropEl.remove(); // bootstrap leaves a modal-backdrop
            }
            const slideshowEl = this.modalEl.querySelector(".modal-body.o_slideshow");
            this.services["public.interactions"].stopInteractions(slideshowEl);
            this.modalEl.removeEventListener("keydown", this.onModalKeydownBound);
            this.modalEl.remove();
            this.modalEl = undefined;
        });

        this.modalEl.addEventListener("shown.bs.modal", () => {
            const slideshowEl = this.modalEl.querySelector(".modal-body.o_slideshow");
            this.services["public.interactions"].startInteractions(slideshowEl);
            this.modalEl.addEventListener("keydown", this.onModalKeydownBound);
        }, { once: true });

        this.insert(this.modalEl, document.body);
        const modalBS = new Modal(this.modalEl, { keyboard: true, backdrop: true });
        modalBS.show();
    }

    /**
     * @param {MouseEvent} ev
     */
    onModalKeydown(ev) {
        if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
            const side = ev.key === "ArrowLeft" ? "prev" : "next";
            this.modalEl.querySelector(`.carousel-control-${side}`).click();
        }
        if (ev.key === "Escape") {
            // If the user is connected as an editor, prevent the backend header from collapsing.
            ev.stopPropagation();
        }
    }

    /**
     * Shows gallery items that are hidden by expandable option.
     */
    expandGallery() {
        const showMoreButtonEl = this.el.querySelector("#btn-expand-gallery");
        const hideExtraButtonEl = this.el.querySelector("#btn-collapse-gallery");

        if (!showMoreButtonEl || !hideExtraButtonEl) {
            return;
        }

        // Toggle expandable control buttons visibility
        showMoreButtonEl.classList.add("d-none");
        hideExtraButtonEl.classList.remove("d-none");

        const maxAllowedItemCount =
            parseInt(this.el.dataset.expandableCount, 10) || galleryItemEls.length;
        const galleryItemEls = wUtils.getSortedGalleryItems(this.el, [".o_grid_item"]);
        galleryItemEls
            .slice(maxAllowedItemCount) // Selects the gallery items beyond allowed limit
            .forEach((galleryItemEl) =>
                // Show all the hidden gallery items
                galleryItemEl.classList.remove("d-none")
            );
    }

    /**
     * Hides gallery items that should be hidden by expandable options
     *
     * @param {{ scrollGalleryIntoView?: boolean }} options - Options for
     *                                            controlling collapse behavior.
     * @param {boolean} [options.scrollGalleryIntoView=true] - Determines if the
     *                                          gallery should scroll into view.
     */
    collapseGallery({ scrollGalleryIntoView = true } = {}) {
        const showMoreButtonEl = this.el.querySelector("#btn-expand-gallery");
        const hideExtraButtonEl = this.el.querySelector("#btn-collapse-gallery");

        if (!showMoreButtonEl || !hideExtraButtonEl) {
            return;
        }

        const maxAllowedItemCount =
            parseInt(this.el.dataset.expandableCount, 10) || galleryItemEls.length;
        const galleryItemEls = wUtils.getSortedGalleryItems(this.el, [".o_grid_item"]);
        galleryItemEls
            .slice(maxAllowedItemCount) // Selects the gallery items beyond allowed limit
            .forEach((galleryItemEl) =>
                // Hide items that are beyond allowed limit
                galleryItemEl.classList.add("d-none")
            );

        // Toggle expandable control buttons visibility
        if (galleryItemEls.length > maxAllowedItemCount) {
            hideExtraButtonEl.classList.add("d-none");
            showMoreButtonEl.classList.remove("d-none");
        }

        // Bring the gallery into view if needed
        if (scrollGalleryIntoView) {
            showMoreButtonEl.scrollIntoView({
                behavior: "smooth",
                block: "end",
            });
        }
    }
}

registry
    .category("public.interactions")
    .add("website.gallery", Gallery);
