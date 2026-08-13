import { usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class ImagePopUp extends Interaction {
    static selector = "img.o_image_popup";
    dynamicContent = {
        _root: {
            "t-on-click": this.onClickImg,
        },
    };

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
    }

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
            getIndicatorLabel: (itemPosition, total) =>
                _t("Slide %(itemPosition)s of %(total)s", { itemPosition, total }),
        })[0];
        this.insert(this.modalEl, document.body);
        const modal = this.bootstrap.getOrCreateInstance(Modal, this.modalEl, {
            keyboard: true,
            backdrop: true,
        });
        const disposeModal = () => {
            this.bootstrap.disposeBootstrapInstance(modal);
            this.modalEl.remove();
        };
        this.addListener(this.modalEl, "hidden.bs.modal", disposeModal, { once: true });
        this.registerCleanup(disposeModal);
        modal.show();
    }
}

registry.category("public.interactions").add("website.image_popup", ImagePopUp);
