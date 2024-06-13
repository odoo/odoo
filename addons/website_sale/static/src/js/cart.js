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
        $(ev.currentTarget).closest('.o_cart_product').find('.js_quantity').val(0).trigger('change');
    },
});

export default publicWidget.registry.websiteSaleCart;
