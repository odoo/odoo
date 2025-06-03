import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

export class ImagePopUp extends Interaction {
    static selector = ".o_image_popup:not(.s_image_gallery .o_image_popup)";
    dynamicContent = {
        _root: {
            "t-on-click": this.onClickImg,
        },
    };

    setup() {
        this.modalEl = null;
    }

    /**
     * Handles click on image to open a custom Bootstrap modal without carousel.
     * @param {MouseEvent} ev
     */
    onClickImg(ev) {
        const clickedEl = ev.currentTarget;
        if (this.modalEl || clickedEl.closest("a")) return;

        const clone = clickedEl.cloneNode(true);
        const lightboxTemplate = "website.image.lightbox";

        this.modalEl = renderToElement(lightboxTemplate, {
            image: clone,
        });

        this.onModalKeydownBound = this.onModalKeydown.bind(this);
        this.onLightboxClickBound = this.onLightboxClick.bind(this);

        this.modalEl.addEventListener("hidden.bs.modal", () => {
            this.modalEl.classList.add("d-none");
            for (const backdropEl of this.modalEl.querySelectorAll(".modal-backdrop")) {
                backdropEl.remove();
            }
            const popupEl = this.modalEl.querySelector(".modal-body.o_slideshow");
            this.services["public.interactions"].stopInteractions(popupEl);
            this.modalEl.removeEventListener("keydown", this.onModalKeydownBound);
            this.modalEl.removeEventListener("click", this.onLightboxClickBound);
            this.modalEl.remove();
            this.modalEl = undefined;
        });

        this.modalEl.addEventListener("shown.bs.modal", () => {
            const popupEl = this.modalEl.querySelector(".modal-body.o_slideshow");
            this.services["public.interactions"].startInteractions(popupEl);
            this.modalEl.addEventListener("keydown", this.onModalKeydownBound);
            this.modalEl.addEventListener("click", this.onLightboxClickBound);
        }, { once: true });

        this.insert(this.modalEl, document.body);
        const modalBS = new Modal(this.modalEl, { keyboard: true, backdrop: true });
        modalBS.show();
    }

    /**
     * Close modal when clicking outside the image.
     * @param {ClickEvent} ev
     */
    onLightboxClick(ev) {
        if (ev.target.nodeName !== 'IMG') {
            const modalInstance = Modal.getInstance(this.modalEl);
            if (modalInstance) {
                modalInstance.hide();
            }
        }
    }

    onModalKeydown(ev) {
        if (ev.key === "Escape") {
            ev.stopPropagation();
        }
    }
}

registry
    .category("public.interactions")
    .add("website.image_popup", ImagePopUp);
