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
        'click #add_to_cart, #products_grid .product_price .a-submit': '_onClickAdd',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this._handleAdd = _.debounce(this._handleAdd.bind(this), 200, true);
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
        this._handleAdd($(ev.currentTarget).closest('form'));
    },

    /**
     * Initializes the optional products modal
     * and add handlers to the modal events (confirm, back, ...)
     *
     * @private
     * @param {$.Element} $form the related webshop form
     */
    _handleAdd: function ($form) {
        this.$form = $form;

        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];

        this.rootProduct = {
            product_id: parseInt($form.find(productSelector.join(', ')).first().val(), 10),
            quantity: parseFloat($form.find('input[name="add_qty"]').val() || 1),
            product_custom_variant_values: this.getCustomVariantValues($form.find('.js_product'))
        };

        this.isWebsite = true;
        this.optionalProductsModal = new OptionalProductsModal($form, {
            rootProduct: this.rootProduct,
            isWebsite: true,
            okButtonText: _t('Proceed to Checkout'),
            cancelButtonText: _t('Continue Shopping'),
            title: _t('Add to cart')
        }).open();

        this.optionalProductsModal.on('options_empty', null, this._onModalOptionsEmpty.bind(this));
        this.optionalProductsModal.on('confirm', null, this._onModalConfirm.bind(this));
        this.optionalProductsModal.on('back', null, this._onModalBack.bind(this));
    },

    /**
     * No optional products found for this product
     * Add custom variant values in the form data and trigger submit
     *
     * @private
     */
    _onModalOptionsEmpty: function () {
        var $productCustomVariantValues = $('<input>', {
            name: 'product_custom_variant_values',
            type: "hidden",
            value: JSON.stringify(this.rootProduct.product_custom_variant_values)
        });
        this.$form.append($productCustomVariantValues);
        this.$form.trigger('submit', [true]);
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
     * - product_custom_variant_values: The products custom variant values
     *
     * @private
     * @param {Boolean} goToShop Triggers a page refresh to the url "shop/cart"
     */
    _onModalSubmit: function (goToShop){
        var productCustomVariantValues = JSON.stringify(
            this.optionalProductsModal.getSelectedProducts()
        );

        this.$form.ajaxSubmit({
            url:  '/shop/cart/update_option',
            data: {
                lang: weContext.get().lang,
                product_custom_variant_values: productCustomVariantValues
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
