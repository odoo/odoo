/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import '@website_sale_comparison/js/website_sale_comparison';

publicWidget.registry.ProductComparison.include({
    events: Object.assign({}, publicWidget.registry.ProductComparison.prototype.events, {
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
