odoo.define('website_sale_product_configurator.OptionalProductsModal', function (require) {
    "use strict";

const { OptionalProductsModal } = require('@sale_product_configurator/js/product_configurator_modal');

OptionalProductsModal.include({
    /**
     * If the "isWebsite" param is true, will also disable the following events:
     * - change [data-attribute_exclusions]
     * - click button.js_add_cart_json
     *
     * This has to be done because those events are already registered at the "website_sale"
     * component level.
     * This modal is part of the form that has these events registered and we
     * want to avoid duplicates.
     *
     * @override
     * @param {$.Element} parent The parent container
     * @param {Object} params
     * @param {boolean} params.isWebsite If we're on a web shop page, we need some
     *   custom behavior
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.isWebsite = params.isWebsite;
        this.forceDialog = params.forceDialog;

        this.dialogClass = 'oe_advanced_configurator_modal' + (params.isWebsite ? ' oe_website_sale' : '');
    },
    /**
     * @override
     * @private
     */
    _triggerPriceUpdateOnChangeQuantity: function () {
        return !this.isWebsite;
    }
});

});
