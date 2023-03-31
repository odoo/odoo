/** @odoo-module **/

import publicWidget from "web.public.widget";

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
        const search = $.deparam(window.location.search.substring(1));
        delete search.min_price;
        delete search.max_price;
        if (parseFloat(range.min) !== range.valueLow) {
            search['min_price'] = range.valueLow;
        }
        if (parseFloat(range.max) !== range.valueHigh) {
            search['max_price'] = range.valueHigh;
        }
        let product_list_div = this.el.querySelector('.o_wsale_products_grid_table_wrapper');
        if (product_list_div) {
            product_list_div.classList.add('opacity-50');
        }
        window.location.search = $.param(search);
    },
});
