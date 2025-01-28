import { patch } from "@web/core/utils/patch";
import { Popup } from "@website/interactions/popup/popup";

patch(Popup.prototype, {
    /**
     * @override
     */
    canBtnPrimaryClosePopup(primaryBtnEl) {
        return (
            super.canBtnPrimaryClosePopup(...arguments)
            && !primaryBtnEl.classList.contains("js_add_cart")
        );
    },
});
