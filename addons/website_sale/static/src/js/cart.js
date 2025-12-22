/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteSaleCart = publicWidget.Widget.extend({
    selector: '.oe_website_sale .oe_cart',
    events: {
        'click .js_delete_product': '_onClickDeleteProduct',
    },

    /**
     * @override
     */
    async start() {
        document.querySelector('.o_cta_navigation_placeholder')?.classList.remove('d-none')
        const ctaContainer = document.querySelector('.o_cta_navigation_container');
        if (ctaContainer) {
            const placeholder = document.querySelector('.o_cta_navigation_placeholder');
            placeholder.style.height = `${ctaContainer.offsetHeight}px`;
            ctaContainer.style.top = `calc(100% - ${ctaContainer.offsetHeight}px)`;
        }
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
