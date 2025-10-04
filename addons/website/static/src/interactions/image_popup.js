import { registry } from "@web/core/registry";
import { BaseLightbox } from "./base_lightbox_popup";

export class ImagePopUp extends BaseLightbox {
    static selector = "img.o_image_popup:not(.s_image_gallery .o_image_popup)";
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
        this.openLightbox("website.image_mirror.lightbox", {
            images: [clone],
            index: 0,
            shouldShowControls: this.hasMultipleImages,
        });
    }
}

registry.category("public.interactions").add("website.image_popup", ImagePopUp);
