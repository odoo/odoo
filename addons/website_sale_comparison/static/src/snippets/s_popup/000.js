/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { Component } from "@odoo/owl";

const CookiesBar = publicWidget.registry.cookies_bar;

CookiesBar.include({

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onHideModal() {
        this._destroyScssProductComparisonButton();
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _showPopup() {
        this._super(...arguments);
        const productCompareButtonEl = document.querySelector(".o_product_feature_panel");
        if (productCompareButtonEl) {
            Component.env.bus.trigger("cookiebar_open");
        }
    },
    /**
     * @private
     * Remove the custom css for `--move-cookie-over-modal`, to position the
     * compare button at the bottom.
     */
    _destroyScssProductComparisonButton() {
        document.querySelector(".o_product_feature_panel")?.style.removeProperty("--move-cookie-over-modal");
    },
});
