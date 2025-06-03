import { Interaction } from "@web/public/interaction";

export class BaseLightbox extends Interaction {
    setup() {
        this.modalEl = null;
        this.onModalKeydownBound = this.onModalKeydown.bind(this);
        this.onLightboxClickBound = this.onLightboxClick.bind(this);
        this.hasMultipleImages = false;
    }

    /**
     * Opens a generic lightbox modal
     * @param {string} template - QWeb template name
     * @param {Object} context - rendering context
     */
    openLightbox(template, context) {
        this.modalEl = this.renderAt(template, context)[0];

        this.addListener(this.modalEl, "hidden.bs.modal", () => {
            this.modalEl.classList.add("d-none");

            for (const backdropEl of this.modalEl.querySelectorAll(".modal-backdrop")) {
                backdropEl.remove();
            }

            const body = this.modalEl.querySelector(".modal-body.o_slideshow");
            this.services["public.interactions"].stopInteractions(body);

            this.modalEl.removeEventListener("keydown", this.onModalKeydownBound);
            this.modalEl.removeEventListener("click", this.onLightboxClickBound);
            this.modalEl.remove();
            this.modalEl = null;
        });

        this.addListener(
            this.modalEl,
            "shown.bs.modal",
            () => {
                const bodyEl = this.modalEl.querySelector(".modal-body.o_slideshow");
                this.services["public.interactions"].startInteractions(bodyEl);
                this.modalEl.addEventListener("keydown", this.onModalKeydownBound);
                this.modalEl.addEventListener("click", this.onLightboxClickBound);
            },
            { once: true }
        );

        this.insert(this.modalEl, document.body);

        const modalBS = new Modal(this.modalEl, { keyboard: true, backdrop: true });
        modalBS.show();
    }

    /**
     * Called when a key is pressed while the modal is focused.
     * - Escape closes the modal
     * - ArrowLeft and ArrowRight navigate through images if there are multiple images
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
