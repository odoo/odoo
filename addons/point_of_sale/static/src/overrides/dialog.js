import { useExternalListener } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import { SIZES, utils } from "@web/core/ui/ui_service";

patch(Dialog.prototype, {
    setup() {
        super.setup();
        if (utils.getSize() <= SIZES.SM) {
            useExternalListener(window, "touchstart", (ev) => {
                if (ev.target.classList.contains("modal")) {
                    this.dismiss();
                }
            });
        }
    },
    async dismiss() {
        if (utils.getSize() > SIZES.SM) {
            return super.dismiss();
        }
        if (odoo.test_mode_enabled) {
            // in tours we must close the popup instantly, as the tour will not wait for
            // the closing before going to the next step
            return super.dismiss();
        }
        this.modalRef.el.classList.add("closing-modal-bg");
        this.modalRef.el.children[0].classList.add("isClosing");
        this.modalRef.el.style.background = "rgba(0, 0, 0, 0)";
        const CLOSING_ANIMATION_DURATION = 200;
        setTimeout(() => {
            super.dismiss();
        }, CLOSING_ANIMATION_DURATION);
    },
});
