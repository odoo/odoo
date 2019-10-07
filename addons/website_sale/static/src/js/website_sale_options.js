odoo.define('website_sale_options.website_sale', function (require) {
'use strict';

var core = require('web.core');
var _t = core._t;
var OptionalProductsModal = require('sale.OptionalProductsModal');
var weContext = require('web_editor.context');
var sAnimations = require('website.content.snippets.animation');
var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
require('website_sale.website_sale');

sAnimations.registry.WebsiteSaleOptions = sAnimations.Class.extend(ProductConfiguratorMixin, {
    selector: '.oe_website_sale',
    read_events: {
        'click #add_to_cart, #products_grid .product_price .a-submit': 'async _onClickAdd',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.isWebsite = true;

        delete this.events['change .css_attribute_color input'];
        delete this.events['change .main_product:not(.in_cart) input.js_quantity'];
        delete this.events['change [data-attribute_exclusions]'];
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Prevents the default submit to allow showing product options
     * in a modal (if any)
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAdd: function (ev) {
        ev.preventDefault();
        return this._handleAdd($(ev.currentTarget).closest('form'));
    },

    /**
     * Initializes the optional products modal
     * and add handlers to the modal events (confirm, back, ...)
     *
     * @private
     * @param {$.Element} $form the related webshop form
     */
    _handleAdd: function ($form) {
        var self = this;
        this.$form = $form;
        this.isWebsite = true;

        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];

        var productReady = this.selectOrCreateProduct(
            $form,
            parseInt($form.find(productSelector.join(', ')).first().val(), 10),
            $form.find('.product_template_id').val(),
            false
        );

        return productReady.done(function (productId) {
            $form.find(productSelector.join(', ')).val(productId);

            self.rootProduct = {
                product_id: productId,
                quantity: parseFloat($form.find('input[name="add_qty"]').val() || 1),
                product_custom_attribute_values: self.getCustomVariantValues($form.find('.js_product')),
                variant_values: self.getSelectedVariantValues($form.find('.js_product')),
                no_variant_attribute_values: self.getNoVariantAttributeValues($form.find('.js_product'))
            };

            self.optionalProductsModal = new OptionalProductsModal($form, {
                rootProduct: self.rootProduct,
                isWebsite: true,
                okButtonText: _t('Proceed to Checkout'),
                cancelButtonText: _t('Continue Shopping'),
                title: _t('Add to cart')
            }).open();

            self.optionalProductsModal.on('options_empty', null, self._onModalOptionsEmpty.bind(self));
            self.optionalProductsModal.on('update_quantity', null, self._onOptionsUpdateQuantity.bind(self));
            self.optionalProductsModal.on('confirm', null, self._onModalConfirm.bind(self));
            self.optionalProductsModal.on('back', null, self._onModalBack.bind(self));

            return self.optionalProductsModal.opened();
        });
    },

    /**
     * No optional products found for this product
     * Add custom variant values and attribute values that do not generate variants
     * in the form data and trigger submit
     *
     * @private
     */
    _onModalOptionsEmpty: function () {
        var $productCustomVariantValues = $('<input>', {
            name: 'product_custom_attribute_values',
            type: "hidden",
            value: JSON.stringify(this.rootProduct.product_custom_attribute_values)
        });
        this.$form.append($productCustomVariantValues);

        var $productNoVariantAttributeValues = $('<input>', {
            name: 'no_variant_attribute_values',
            type: "hidden",
            value: JSON.stringify(this.rootProduct.no_variant_attribute_values)
        });
        this.$form.append($productNoVariantAttributeValues);

        this.$form.trigger('submit', [true]);
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
     * Submit form and stay on the same page
     *
     * @private
     */
    _onModalBack: function () {
        this._onModalSubmit(false);
    },

    /**
     * Submit form and go to shop
     *
     * @private
     */
    _onModalConfirm: function () {
        this._onModalSubmit(true);
    },

    /**
     * Submits the form with additional parameters
     * - lang
     * - product_custom_attribute_values: The products custom variant values
     *
     * @private
     * @param {Boolean} goToShop Triggers a page refresh to the url "shop/cart"
     */
    _onModalSubmit: function (goToShop){
        var customValues = JSON.stringify(
            this.optionalProductsModal.getSelectedProducts()
        );

        this.$form.ajaxSubmit({
            url:  '/shop/cart/update_option',
            data: {
                lang: weContext.get().lang,
                custom_values: customValues
            },
            success: function (quantity) {
                if (goToShop) {
                    var path = window.location.pathname.replace(/shop([\/?].*)?$/, "shop/cart");
                    window.location.pathname = path;
                }
                var $quantity = $(".my_cart_quantity");
                $quantity.parent().parent().removeClass("d-none", !quantity);
                $quantity.html(quantity).hide().fadeIn(600);
            }
        });
    },
});

return sAnimations.registry.WebsiteSaleOptions;

});
