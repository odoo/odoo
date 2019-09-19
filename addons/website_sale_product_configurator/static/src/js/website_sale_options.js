odoo.define('website_sale_options.website_sale', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
var OptionalProductsModal = require('sale_product_configurator.OptionalProductsModal');
require('website_sale.website_sale');

var _t = core._t;

publicWidget.registry.WebsiteSale.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onProductReady: function () {
        this.optionalProductsModal = new OptionalProductsModal(this.$form, {
            rootProduct: this.rootProduct,
            isWebsite: true,
            okButtonText: _t('Proceed to Checkout'),
            cancelButtonText: _t('Continue Shopping'),
            title: _t('Add to cart'),
            context: this._getContext(),
        }).open();

        this.optionalProductsModal.on('options_empty', null, this._submitForm.bind(this));
        this.optionalProductsModal.on('update_quantity', null, this._onOptionsUpdateQuantity.bind(this));
        this.optionalProductsModal.on('confirm', null, this._onModalSubmit.bind(this, true));
        this.optionalProductsModal.on('back', null, this._onModalSubmit.bind(this, false));

        return this.optionalProductsModal.opened();
    },

    /**
     * Update web shop base form quantity
     * when quantity is updated in the optional products window
     *
     * @private
     * @param {integer} quantity
     */
    _onOptionsUpdateQuantity: function (quantity) {
        var $qtyInput = this.$form
            .find('.js_main_product input[name="add_qty"]')
            .first();

        if ($qtyInput.length) {
            $qtyInput.val(quantity).trigger('change');
        } else {
            // This handles the case when the "Select Quantity" customize show
            // is disabled, and therefore the above selector does not find an
            // element.
            // To avoid duplicating all RPC, only trigger the variant change if
            // it is not already done from the above trigger.
            this.optionalProductsModal.triggerVariantChange(this.optionalProductsModal.$el);
        }
    },

    /**
     * Submits the form with additional parameters
     * - lang
     * - product_custom_attribute_values: The products custom variant values
     *
     * @private
     * @param {Boolean} goToShop Triggers a page refresh to the url "shop/cart"
     */
    _onModalSubmit: function (goToShop) {
        var customValues = JSON.stringify(
            this.optionalProductsModal.getSelectedProducts()
        );

        this.$form.ajaxSubmit({
            url:  '/shop/cart/update_option',
            data: {
                lang: this._getContext().lang,
                custom_values: customValues
            },
            success: function (quantity) {
                if (goToShop) {
                    var path = window.location.pathname.replace(/shop([\/?].*)?$/, "shop/cart");
                    window.location.pathname = path;
                }
                var $quantity = $(".my_cart_quantity");
                $quantity.parent().parent().removeClass('d-none');
                $quantity.html(quantity).hide().fadeIn(600);
            }
        });
    },
});

return publicWidget.registry.WebsiteSaleOptions;

});
