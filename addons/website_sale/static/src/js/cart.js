/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteSaleCart = publicWidget.Widget.extend({
    selector: '.oe_website_sale .oe_cart',
    events: {
        'click .js_delete_product': '_onClickDeleteProduct',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickDeleteProduct: function (ev) {
        ev.preventDefault();
        let quantityElement = ev.currentTarget.closest('.o_cart_product').querySelector('.js_quantity');
        quantityElement.value = 0;
        quantityElement.dispatchEvent(new Event('change'));
    },
});

export default publicWidget.registry.websiteSaleCart;
