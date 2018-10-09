odoo.define('sale.OptionalProductsModal', function (require) {
    "use strict";

var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var ServicesMixin = require('web.ServicesMixin');
var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var weContext = require('web_editor.context');

var productNameMap = {};
var optionalProductsMap = {};

var OptionalProductsModal = Dialog.extend(ServicesMixin, ProductConfiguratorMixin, {
    events:  _.extend({}, Dialog.prototype.events, ProductConfiguratorMixin.events, {
        'click a.js_add, a.js_remove': '_onAddOrRemoveOption',
        'change .in_cart.main_product input.js_quantity': '_onChangeQuantity'
    }),
    /**
     * Initializes the optional products modal
     *
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
     * @param {integer} params.pricelistId
     * @param {boolean} params.isWebsite If we're on a web shop page, we need some
     *   custom behavior
     * @param {string} params.okButtonText The text to apply on the "ok" button, typically
     * "Add" for the sale order and "Proceed to checkout" on the web shop
     * @param {string} params.cancelButtonText same as "params.okButtonText" but
     *   for the cancel button
     * @param {Object} params.rootProduct The root product of the optional products window
     * @param {integer} params.rootProduct.product_id
     * @param {integer} params.rootProduct.quantity
     * @param {Array} params.rootProduct.variant_values
     * @param {Array} params.rootProduct.product_custom_attribute_values
     * @param {Array} params.rootProduct.no_variant_attribute_values
     */
    init: function (parent, params) {
        var self = this;

        this._super(parent, {
            size: 'large',
            buttons: [{
                text: params.okButtonText,
                click: this._onConfirmButtonClick,
                classes: 'btn-primary'
            }, {
                text: params.cancelButtonText,
                click: this._onCancelButtonClick
            }],
            title: params.title
        });

        this.rootProduct = params.rootProduct;
        this.container = parent;
        this.pricelistId = params.pricelistId;
        this.isWebsite = params.isWebsite;
        this.dialogClass = 'oe_optional_products_modal' + (params.isWebsite ? ' oe_website_sale' : '');

        if (this.isWebsite) {
            delete this.events['change [data-attribute_exclusions]'];
            delete this.events['click button.js_add_cart_json'];
        }

        this._opened.then(function () {
            self.triggerVariantChange(self.$el);
        });
    },
     /**
     * @override
     */
    willStart: function () {
        var self = this;

        var uri = this._getUri("/product_configurator/show_optional_products");
        var getModalContent = ajax.jsonRpc(uri, 'call', {
            product_id: self.rootProduct.product_id,
            variant_values: self.rootProduct.variant_values,
            pricelist_id: self.pricelistId,
            kwargs: {
                context: _.extend({
                    'quantity': self.rootProduct.quantity
                }, weContext.get()),
            }
        })
        .then(function (modalContent) {
            if (modalContent){
                var $modalContent = $(modalContent);
                $modalContent = self._postProcessContent($modalContent);
                self.$content = $modalContent;
            } else {
                self.trigger('options_empty');
                self.preventOpening = true;
            }
        });

        var parentInit = self._super.apply(self, arguments);
        return $.when(getModalContent, parentInit);
    },

    /**
     * This is overridden to append the modal to the provided container (see init("parent")).
     * We need this to have the modal contained in the web shop product form.
     * The additional products data will then be contained in the form and sent on submit.
     *
     * @override
     */
    open: function (options) {
        $('.tooltip').remove(); // remove open tooltip if any to prevent them staying when modal is opened

        var self = this;
        this.appendTo($('<div/>')).then(function () {
            if (!self.preventOpening){
                self.$modal.find(".modal-body").replaceWith(self.$el);
                self.$modal.attr('open', true);
                self.$modal.removeAttr("aria-hidden");
                self.$modal.modal().appendTo(self.container);
                self._opened.resolve();
            }
        });
        if (options && options.shouldFocusButtons) {
            self._onFocusControlButton();
        }

        return self;
    },
    /**
     * Will update quantity input to synchronize with previous window
     *
     * @override
     */
    start: function (){
        this._super.apply(this, arguments);

        this.$el.find('input[name="add_qty"]').val(this.rootProduct.quantity);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the list of selected products.
     * The root product is added on top of the list.
     *
     * @returns {Array} products
     *   {integer} product_id
     *   {integer} quantity
     *   {Array} product_custom_variant_values
     *   {Array} no_variant_attribute_values
     * @public
     */
    getSelectedProducts: function () {
        var self = this;
        var products = [this.rootProduct];
        this.$modal.find('.js_product.in_cart:not(.main_product)').each(function (){
            var quantity = 0;
            var $item = $(this);
            if ($item.find('input[name="add_qty"]').length){
                quantity = $item.find('input[name="add_qty"]').val();
            } else {
                quantity = parseInt(
                    $item
                        .find('.optional_product_quantity span.add_qty')
                        .html()
                        .trim()
                );
            }

            var productCustomVariantValues = self.getCustomVariantValues($(this));
            var noVariantAttributeValues = self.getNoVariantAttributeValues($(this));
            products.push({
                product_id: parseInt($item.find('input.product_id').val()),
                quantity: quantity,
                product_custom_attribute_values: productCustomVariantValues,
                no_variant_attribute_values: noVariantAttributeValues
            });
        });

        return products;
    },

    // ------------------------------------------
    // Private
    // ------------------------------------------

    /**
     * Adds the product image and updates the product description
     * based on attribute values that are either "no variant" or "custom".
     *
     * @private
     */
    _postProcessContent: function ($modalContent) {
        var productId = this.rootProduct.product_id;
        $modalContent
            .find('img:first')
            .attr("src", "/web/image/product.product/" + productId + "/image_medium");

        if (this.rootProduct &&
                (this.rootProduct.product_custom_attribute_values ||
                 this.rootProduct.no_variant_attribute_values)) {
            var $productDescription = $modalContent
                .find('.main_product')
                .find('td.td-product_name div.text-muted.small');
            var description = $productDescription.html();

            $.each(this.rootProduct.product_custom_attribute_values, function (){
                description += '<br/>' + this.attribute_value_name + ': ' + this.custom_value;
            });

            $.each(this.rootProduct.no_variant_attribute_values, function (){
                if (this.is_custom !== 'True'){
                    description += '<br/>' + this.attribute_name + ': ' + this.attribute_value_name;
                }
            });

            $productDescription.html(description);
        }

        return $modalContent;
    },

    /**
     * @private
     */
    _onConfirmButtonClick: function () {
        this.trigger('confirm');
        this.close();
    },

    /**
     * @private
     */
    _onCancelButtonClick: function () {
        this.trigger('back');
        this.close();
    },

    /**
     * Will add/remove the option, that includes:
     * - Moving it to the correct DOM section
     *   and possibly under its parent product
     * - Hiding attribute values selection and showing the quantity
     * - Creating the product if it's in "dynamic" mode (see product_attribute.create_variant)
     * - Updating the description based on custom/no_create attribute values
     * - Removing optional products if parent product is removed
     * - Computing the total price
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onAddOrRemoveOption: function (ev){
        ev.preventDefault();
        var self = this;
        var $target = $(ev.currentTarget);
        var $modal = $target.parents('.oe_optional_products_modal');
        var $parent = $target.parents('.js_product:first');
        $parent.find("a.js_add, span.js_remove").toggleClass('d-none');
        $parent.find("input.js_optional_same_quantity").val($target.hasClass("js_add") ? 1 : 0 );
        $parent.find(".js_remove");

        var productTemplateId = $parent.find(".product_template_id").val();
        if ($target.hasClass('js_add')) {
            self._onAddOption($modal, $parent ,productTemplateId);
        } else {
            self._onRemoveOption($modal, $parent ,productTemplateId);
        }

        self.computePriceTotal();
    },

    /**
     * @private
     * @see _onAddOrRemoveOption
     * @param {$.Element} $modal
     * @param {$.Element} $parent
     * @param {integer} productTemplateId
     */
    _onAddOption: function ($modal, $parent, productTemplateId) {
        var self = this;
        var $main_product = $modal.find('.js_product:first');
        var $selectOptionsText = $modal.find('.o_select_options');

        // remove attribute values selection and move quantity to the correct table spot (".td-qty"))
        $parent.addClass('in_cart');
        $parent.find('.td-qty').addClass('text-center');
        $parent.find('.td-qty').append($parent.find('.optional_product_quantity'));

        // change product name to display_name (containing attribute values) when it's added to cart
        // the "simple" name is kept into a map to revert to it if the product is removed from the cart
        productNameMap[productTemplateId] = $parent.find(".product-name").html();
        $parent.find(".product-name").html($parent.find(".product_display_name").val());

        var productCustomVariantValues = self.getCustomVariantValues($parent);
        var noVariantAttributeValues = self.getNoVariantAttributeValues($parent);
        if (productCustomVariantValues || noVariantAttributeValues) {
            var $productDescription = $parent
                .find('td.td-product_name div.float-left');

            var description = '';
            $.each(productCustomVariantValues, function (){
                description += '<br/>' + this.attribute_value_name + ': ' + this.custom_value;
            });

            $.each(noVariantAttributeValues, function (){
                if (this.is_custom !== 'True'){
                    description += '<br/>' + this.attribute_name + ': ' + this.attribute_value_name;
                }
            });

            var $customAttributeValuesDescription = $('<div>', {
                class: 'custom_attribute_values_description text-muted small',
                html: description
            });

            $productDescription.append($customAttributeValuesDescription);
        }

        // if it's an optional product of an optional product, place it after it's parent
        var parentProductId = null;
        for (var productIdKey in optionalProductsMap) {
            if (optionalProductsMap[productIdKey].indexOf(productTemplateId) !== -1) {
                parentProductId = productIdKey;
                break;
            }

            $('tr:last').after($parent);
        }

        if (parentProductId) {
            $modal.find('.product_template_id').filter(function () {
                return parentProductId === $(this).val();
            }).parents('.js_product:first').after($parent);
        } else {
            // else, place it after the main product
            $main_product.after($parent);
        }

        var productReady = this.selectOrCreateProduct(
            $parent,
            $parent.find('.product_id').val(),
            productTemplateId,
            true
        );

        productReady.done(function (productId){
            $parent.find('.product_id').val(productId);

            ajax.jsonRpc(self._getUri("/product_configurator/optional_product_items"), 'call', {
                'product_id': productId,
                'pricelist_id': self.pricelistId
            }).then(function (addedItem) {
                var $addedItem = $(addedItem);
                $modal.find('tr:last').after($addedItem);

                self.$el.find('input[name="add_qty"]').trigger('change');
                self.triggerVariantChange($addedItem);

                if ($addedItem.find(".product_template_id").length > 0) {
                    // we need to map this product with it's optional products to be able to:
                    // - remove them from the cart if the parent product is removed
                    // - place the optional products under their parent in
                    //   the interface when they're added to the cart
                    optionalProductsMap[productTemplateId] = $addedItem
                        .find(".product_template_id")
                        .map(function () {
                            return $(this).val();
                    }).get();
                }

                if ($selectOptionsText.nextAll('.js_product').length === 0){
                    // no more optional products to select -> hide the header
                    $selectOptionsText.hide();
                }
            });
        });
    },

    /**
     * @private
     * @see _onAddOrRemoveOption
     * @param {$.Element} $modal
     * @param {$.Element} $parent
     * @param {integer} productTemplateId
     */
    _onRemoveOption: function ($modal, $parent, productTemplateId){
        // restore attribute values selection
        $parent.removeClass('in_cart');
        $parent.find('.td-qty').removeClass('text-center');
        $parent.find('.js_remove.d-none').prepend($parent.find('.optional_product_quantity'));
        $parent.find('.custom_attribute_values_description').remove();

        var $select_options_text = $modal.find('.o_select_options');
        $select_options_text.show();

        // revert back to original product name and clean the entry
        $parent.find(".product-name").html(productNameMap[productTemplateId]);
        delete productNameMap[productTemplateId];

        this._removeOptionOption($modal, productTemplateId);

        $('tr:last').after($parent);
    },

    /**
     * If the removed product had optional products, remove them as well
     *
     * @private
     * @param {$.Element} $modal
     * @param {integer} optionId The removed optional product id
     */
    _removeOptionOption: function ($modal, optionId) {
        var self = this;
        if (optionalProductsMap[optionId]) {
            optionalProductsMap[optionId].forEach(function (productId) {
                $modal.find('.product_template_id').filter(function () {
                    return productId === $(this).val();
                }).parents('.js_product:first').remove();

                self._removeOptionOption($modal, productId);
            });

            delete optionalProductsMap[optionId];
        }
    },

    /**
     * When the quantity of the root product is updated, we need to update
     * the quantity of all the selected optional products.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeQuantity: function (ev){
        var $quantity = $(ev.currentTarget);
        var qty = parseFloat($quantity.val());
        var $modal = $quantity.parents('.oe_optional_products_modal');
        if (qty === 1) {
            $modal.find(".js_items").addClass('d-none').removeClass('add_qty');
            $modal.find(".js_item").removeClass('d-none').addClass('add_qty');
        } else {
            $modal.find(".js_items").removeClass('d-none').addClass('add_qty').text(qty);
            $modal.find(".js_item").addClass('d-none').removeClass('add_qty');
        }

        this.rootProduct.quantity = qty;

        if (!this.isWebsite){
            this.onChangeAddQuantity(ev);
        }

        this.trigger('update_quantity', qty);
    }
});

return OptionalProductsModal;

});