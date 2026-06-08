import { registry } from "@web/core/registry";

import { Interaction } from "@web/public/interaction";

export class BaseLightbox extends Interaction {
    static selector = ".modal.o_image_lightbox";
    dynamicContent = {
        _root: {
            "t-on-hidden.bs.modal": this.onModalHidden,
            "t-on-keydown": this.onModalKeydown,
            "t-on-click": this.onLightboxClick,
        },
    };

    setup() {
        this.modalEl = this.el;
        this.hasMultipleImages = this.modalEl.querySelectorAll("img").length
            ? this.el.querySelectorAll("img").length > 1
            : false;
    }

    /**
     * Called when the modal is hidden. Cleans up the modal element.
     */
    onModalHidden() {
        this.modalEl.classList.add("d-none");
        for (const backdropEl of this.modalEl.querySelectorAll(".modal-backdrop")) {
            backdropEl.remove();
        }
        this.modalEl.remove();
        this.modalEl = null;
    }

    /**
     * Called when a key is pressed while the modal is focused.
     * - Escape closes the modal
     * - ArrowLeft and ArrowRight navigate through images if there are
     *   multiple images
     *
     * @param {KeyboardEvent} ev
     */
    onModalKeydown(ev) {
        if (ev.key === "Escape") {
            // If the user is connected as an editor, prevent the backend header from collapsing.
            ev.stopPropagation();
        }
        if (this.hasMultipleImages && (ev.key === "ArrowLeft" || ev.key === "ArrowRight")) {
            const side = ev.key === "ArrowLeft" ? "prev" : "next";
            this.modalEl.querySelector(`.carousel-control-${side}`).click();
        }
    }

    /**
     * Close the modal when clicking outside of the image if there is only one image.
     * @param {MouseEvent} ev
     */
    onLightboxClick(ev) {
        if (!this.hasMultipleImages && ev.target.nodeName !== "IMG") {
            const modalInstance = Modal.getInstance(this.modalEl);
            if (modalInstance) {
                modalInstance.hide();
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website.base_lightbox", BaseLightbox);
