import { patch } from "@web/core/utils/patch";
import { Popup } from "@website/interactions/popup/popup";

patch(Popup.prototype, {
    /**
     * Prevents the (newsletter) popup to be shown if the user is subscribed.
     *
     * @override
     */
    canShowPopup() {
        if (
            this.el.classList.contains("o_newsletter_popup")
            // js_subscribe_email is kept by compatibility (it was the old name
            // of js_subscribe_value)
            && this.el.querySelector("input.js_subscribe_value, input.js_subscribe_email")?.disabled
        ) {
            return false;
        }
        return super.canShowPopup(...arguments);
    },
    /**
     * @override
     */
    canBtnPrimaryClosePopup(primaryBtnEl) {
        if (primaryBtnEl.classList.contains("js_subscribe_btn")) {
            return false;
        }
        return super.canBtnPrimaryClosePopup(...arguments);
    },
});
