/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const CookiesBar = publicWidget.registry.cookies_bar;

CookiesBar.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     *
     * Resolved the issue where the compare button was hidden due to the modal
     * appearing over it. Added CSS `--move-cookie-over-modal` to dynamically adjust
     * the position of elements based on modal changes.
     */
    _showPopup() {
        this._super(...arguments);
        const productCompareButtonEl = document.querySelector(".o_product_feature_panel");

        if (productCompareButtonEl) {
            const cookieModelEl = this.el.querySelector(".modal");

            if (cookieModelEl.classList.contains("o_cookies_popup") || !cookieModelEl.classList.contains("s_popup_no_backdrop")) {
                return;
            }

            const cookieModalDialogEl = cookieModelEl.querySelector(".modal-dialog");
            const isCookiebarLarge = cookieModalDialogEl.classList.contains("s_popup_size_full");

            if (isCookiebarLarge) {
                const bottom = cookieModalDialogEl.querySelector(".modal-content").offsetHeight
                    ? `${cookieModalDialogEl.querySelector(".modal-content").offsetHeight}px`
                    : "";
                productCompareButtonEl?.style.setProperty("--move-cookie-over-modal", bottom);
            }
        }
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
    _onHideModal() {
        this._super(...arguments);
        const productPanelEl = document.querySelector(".o_product_feature_panel");
        if (productPanelEl) {
            productPanelEl.style.removeProperty("--move-cookie-over-modal");
        }
    },
});
