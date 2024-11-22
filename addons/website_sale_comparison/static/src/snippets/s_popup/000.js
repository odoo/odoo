/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const CookiesBar = publicWidget.registry.cookies_bar;

CookiesBar.include({
    /**
     * @override
     */
    destroy() {
        this._destroyScssProductComparisonButton();
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAcceptClick() {
        this._destroyScssProductComparisonButton();
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * Remove the custom css for `--move-cookie-over-modal`, to position the
     * compare button at the bottom.
     */
    _destroyScssProductComparisonButton() {
        document.querySelector(".o_product_feature_panel")?.style.removeProperty("--move-cookie-over-modal");
    },
});
