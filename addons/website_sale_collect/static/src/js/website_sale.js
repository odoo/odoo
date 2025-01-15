import { Component } from '@odoo/owl';
import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * Trigger a state update of the ClickAndCollectAvailability component when the combination info
     * is updated.
     *
     * @override
     */
    _onChangeCombination(ev, $parent, combination) {
        const res = this._super.apply(this, arguments);
        Component.env.bus.trigger('updateCombinationInfo', combination);
        return res;
    },

    /**
     * Override of `_updateRootProduct` to skip the quantity check and allow adding a product to the
     * cart via the configurator when Click and Collect is activated.
     *
     * @override
     * @private
     * @param {HTMLFormElement} form - The form in which the product is.
     *
     * @returns {void}
     */
    _updateRootProduct(form) {
        this._super(...arguments);
        this.rootProduct.isClickAndCollectActive = Boolean(
            form.querySelector('.o_click_and_collect_availability')
        );
    },
})
