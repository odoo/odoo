import { CookiesBar } from "@website/interactions/cookies/cookies_bar";
import { patch } from "@web/core/utils/patch";

patch(CookiesBar.prototype, {
    /**
     * @override
     *
     * Resolved the issue where the compare button was hidden due to the modal
     * appearing over it. Added CSS `--move-cookie-over-modal` to dynamically
     * adjust the position of elements based on modal changes.
     */
    showPopup() {
        super.showPopup();
        // Initially when the modal is shown, its height is 0, so we need to
        // wait for the modal to be fully rendered before adjusting the position
        // of the compare button. Through the `--move-cookie-over-modal` CSS
        // variable, we can dynamically adjust the position of elements based on
        // modal changes.
        this.waitForTimeout(() => {
            const productCompareButtonEl = document.querySelector(".o_product_feature_panel");

            if (productCompareButtonEl) {
                const cookieModelEl = this.el.querySelector(".modal");

                if (
                    cookieModelEl.classList.contains("o_cookies_popup") ||
                    !cookieModelEl.classList.contains("s_popup_no_backdrop")
                ) {
                    return;
                }

                const cookieModalDialogEl = cookieModelEl.querySelector(".modal-dialog");
                const isCookiebarLarge =
                    cookieModalDialogEl.classList.contains("s_popup_size_full");

                if (isCookiebarLarge) {
                    const bottom = cookieModalDialogEl.querySelector(".modal-content").offsetHeight
                        ? `${cookieModalDialogEl.querySelector(".modal-content").offsetHeight}px`
                        : "";
                    productCompareButtonEl?.style.setProperty("--move-cookie-over-modal", bottom);
                }
            }
        }, 0);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     *
     * Remove the custom css for `--move-cookie-over-modal`, to position the
     * compare button at the bottom.
     */
    onHideModal() {
        super.onHideModal();
        const productPanelEl = document.querySelector(".o_product_feature_panel");
        if (productPanelEl) {
            productPanelEl.style.removeProperty("--move-cookie-over-modal");
        }
    },
});
