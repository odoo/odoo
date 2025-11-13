import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class ImagePopUp extends Interaction {
    static selector = "img.o_image_popup";
    dynamicContent = {
        _root: {
            "t-on-click": this.onClickImg,
        },
    };

    /**
     * Handles the click on an image with the 'o_image_popup' class.
     * If the image is not inside a link or a modal, opens it in a lightbox.
     * @param {MouseEvent} ev
     */
    onClickImg(ev) {
        if (ev.currentTarget.closest("a") || ev.currentTarget.closest(".modal")) {
            return;
        }

        const clone = ev.currentTarget.cloneNode(true);
        this.hasMultipleImages = false;
        this.modalEl = this.renderAt("website.image_mirror.lightbox", {
            images: [clone],
            index: 0,
            shouldShowControls: this.hasMultipleImages,
        })[0];
        this.insert(this.modalEl, document.body);
        new Modal(this.modalEl, { keyboard: true, backdrop: true }).show();
    }
}

registry
    .category("public.interactions")
    .add("website.image_popup", ImagePopUp);
