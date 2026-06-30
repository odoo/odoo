/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.multirangePriceSelector = publicWidget.Widget.extend({
    selector: '.o_wsale_products_page',
    events: {
        'newRangeValue #o_wsale_price_range_option input[type="range"]': '_onPriceRangeSelected',
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onPriceRangeSelected(ev) {
        const range = ev.currentTarget;
        const searchParams = new URLSearchParams(window.location.search);
        searchParams.delete("min_price");
        searchParams.delete("max_price");
        if (parseFloat(range.min) !== range.valueLow) {
            searchParams.set("min_price", range.valueLow);
        }
        if (parseFloat(range.max) !== range.valueHigh) {
            searchParams.set("max_price", range.valueHigh);
        }
        let product_list_div = this.el.querySelector('.o_wsale_products_grid_table_wrapper');
        if (product_list_div) {
            product_list_div.classList.add('opacity-50');
        }
        window.location.search = searchParams.toString();
    },
});
