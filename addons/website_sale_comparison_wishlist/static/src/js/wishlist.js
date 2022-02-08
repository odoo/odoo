/** @odoo-module **/

import publicWidget from 'web.public.widget';
import 'website_sale_comparison.comparison';

publicWidget.registry.ProductComparison.include({
    events: _.extend({}, publicWidget.registry.ProductComparison.prototype.events, {
        'click .wishlist-section .o_add_to_compare': '_onClickCompare',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickCompare: function (ev) {
        const productID = parseInt(ev.currentTarget.dataset.productId, 10);
        this.productComparison._addNewProducts(productID);
    },
});
