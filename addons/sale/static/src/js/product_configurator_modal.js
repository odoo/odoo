odoo.define('sale.OptionalProductsModal', function (require) {
    "use strict";

var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var ServicesMixin = require('web.ServicesMixin');
var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var weContext = require('web_editor.context');

var product_name_map = {};
var optional_products_map = {};

var OptionalProductsModal = Dialog.extend(ServicesMixin, ProductConfiguratorMixin, {
    events:  _.extend({}, Dialog.prototype.events, ProductConfiguratorMixin.events, {
        'click a.js_add, a.js_remove': '_onAddOrRemoveOption',
        'change input[name="add_qty"]': '_onChangeMainProductQuantity',
        'click .css_attribute_color input': '_onColorClick',
        'change input.js_quantity': '_onChangeQuantity'
    }),
    /**
     * Initializes the optional products modal
     *
     * @override
     */
    init: function (parent, params) {
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
    },
     /**
     * @override
     */
    willStart: function () {
        var self = this;

        var uri = this._getUri("/product_configurator/show_optional_products");
        var getModalContent = ajax.jsonRpc(uri, 'call', {
            product_id: self.rootProduct.product_id,
            pricelist_id: self.pricelistId,
            kwargs: {
                context: _.extend({'quantity': self.rootProduct.quantity}, weContext.get()),
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
     * Show a dialog
     *
     * @param {Object} options
     * @param {boolean} options.shouldFocusButtons  if true, put the focus on
     * the first button primary when the dialog opens
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
     * Will:
     * - trigger add_qty change to synchronize quantity with previous window
     * - trigger variant change to compute the price and other
     *   variant specific changes
     *
     *
     * @override
     */
    start: function (){
        this._super.apply(this, arguments);

        this.$el.find('input[name="add_qty"]').val(this.rootProduct.quantity).change();
        this.triggerVariantChange(this.$el);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the list of selected products as products[{product_id, quantity}]
     *
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
            products.push({
                product_id: parseInt($item.find('input.product_id').val()),
                quantity: quantity,
                product_custom_variant_values: productCustomVariantValues
            });
        });

        return products;
    },

    // ------------------------------------------
    // Private
    // ------------------------------------------

    /**
     * Adds the product image and updates the product description
     *
     * @private
     */
    _postProcessContent: function ($modalContent) {
        var productId = this.rootProduct.product_id;
        $modalContent
            .find('img:first')
            .attr("src", "/web/image/product.product/" + productId + "/image_medium");

        if (this.rootProduct && this.rootProduct.product_custom_variant_values) {
            var $productDescription = $modalContent
                .find('.main_product')
                .find('td.td-product_name div.text-muted.small');
            var description = $productDescription.html();
            $.each(this.rootProduct.product_custom_variant_values, function (){
                description += '<br/>' + this.attribute_value_name + ': ' + this.custom_value;
            });

            $productDescription.html(description);
        }

        return $modalContent;
    },

    /**
     * Website behavior is slightly different from backend so we append
     * "_website" to URLs to lead to a different route
     *
     * @private
     * @param {string} uri The uri to adapt
     */
    _getUri: function (uri) {
        if (this.isWebsite){
            return uri + '_website';
        } else {
            return uri;
        }
    },

    _onConfirmButtonClick: function () {
        this.trigger('confirm');
        this.close();
    },

    _onCancelButtonClick: function () {
        this.trigger('back');
        this.close();
    },

    _onColorClick: function (ev){
        var $modal = $(ev.currentTarget).parents('.oe_optional_products_modal');
        $modal.find('.css_attribute_color').removeClass("active");
        $modal.find('.css_attribute_color:has(input:checked)').addClass("active");

        this._onChangeColorAttribute(ev);
    },

    /**
     * Will add/remove the option, that includes:
     * - Moving it to the correct DOM section
     *   and possibly under its parent product
     * - Hiding variants and showing the quantity
     * - Remove optional products if parent product is removed
     * - Compute the total price
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onAddOrRemoveOption: function (ev){
        ev.preventDefault();
        var self = this;
        var $target = $(ev.currentTarget);
        var $modal = $target.parents('.oe_optional_products_modal');
        var $select_options_text = $modal.find('.o_select_options');
        var $main_product = $modal.find('.js_product:first');
        var $parent = $target.parents('.js_product:first');
        $parent.find("a.js_add, span.js_remove").toggleClass('d-none');
        $parent.find("input.js_optional_same_quantity").val($target.hasClass("js_add") ? 1 : 0 );
        $parent.find(".js_remove");

        var product_id = $parent.find(".product_template_id").val();
        if ($target.hasClass('js_add')) {
            // remove attribute values selection and move quantity to the correct table spot (".td-qty"))
            $parent.addClass('in_cart');
            $parent.find('.td-qty').addClass('text-center');
            $parent.find('.td-qty').append($parent.find('.optional_product_quantity'));

            // change product name to display_name (containing attribute values) when it's added to cart
            // the "simple" name is kept into a map to revert to it if the product is removed from the cart
            product_name_map[product_id] = $parent.find(".product-name").html();
            $parent.find(".product-name").html($parent.find(".product_display_name").val());

            var product_custom_variant_values = self.getCustomVariantValues($parent);
            if (product_custom_variant_values) {
                var $productDescription = $parent
                    .find('td.td-product_name div.float-left');

                var description = '';
                $.each(product_custom_variant_values, function (){
                    description += '<br/>' + this.attribute_value_name + ': ' + this.custom_value;
                });

                var $customAttributeValuesDescription = $('<div>', {
                    class: 'custom_attribute_values_description text-muted small',
                    html: description
                });

                $productDescription.append($customAttributeValuesDescription);
            }

            // if it's an optional product of an optional product, place it after it's parent
            var parent_product_id = null;
            for (var product_id_key in optional_products_map) {
                if (optional_products_map[product_id_key].indexOf(product_id) !== -1) {
                    parent_product_id = product_id_key;
                    break;
                }

                $('tr:last').after($parent);
            }

            if (parent_product_id) {
                $modal.find('.product_template_id').filter(function () {
                    return parent_product_id === $(this).val();
                }).parents('.js_product:first').after($parent);
            } else {
                // else, place it after the main product
                $main_product.after($parent);
            }

            var product_variant_id = $parent.find('.product_id').val();
            ajax.jsonRpc(self._getUri("/product_configurator/optional_product_items"), 'call', {
                'product_id': product_variant_id,
                'pricelist_id': self.pricelistId
            }).then(function (addedItem) {
                var $addedItem = $(addedItem);
                $modal.find('tr:last').after($addedItem);

                // trigger input change to validate fields
                $('.js_add_cart_variants', $addedItem).each(function () {
                    $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
                });

                // update new options quantity
                $modal.find('input[name="add_qty"]').trigger('change');

                if ($addedItem.find(".product_template_id").length > 0) {
                    // we need to map this product with it's optional products to be able to:
                    // - remove them from the cart if the parent product is removed
                    // - place the optional products under their parent in the interface when they're added to the cart
                    optional_products_map[product_id] = $addedItem.find(".product_template_id").map(function () {
                        return $(this).val();
                    }).get();
                }

                if ($select_options_text.nextAll('.js_product').length === 0){
                    // no more optional products to select -> hide the header
                    $select_options_text.hide();
                }
            });
        } else {
            // restore attribute values selection
            $parent.removeClass('in_cart');
            $parent.find('.td-qty').removeClass('text-center');
            $parent.find('.js_remove.d-none').prepend($parent.find('.optional_product_quantity'));
            $parent.find('.custom_attribute_values_description').remove();

            $select_options_text.show();

            // revert back to original product name and clean the entry
            $parent.find(".product-name").html(product_name_map[product_id]);
            delete product_name_map[product_id];

            if (optional_products_map[product_id]) {
                // if the removed product had optional products, remove them as well
                optional_products_map[product_id].forEach(function (productId) {
                    $modal.find('.product_template_id').filter(function () {
                        return productId === $(this).val();
                    }).parents('.js_product:first').remove();
                });
                delete optional_products_map[product_id];
            }

            $('tr:last').after($parent);
        }

        self.computePriceTotal();
    },

    _onChangeQuantity: function (ev){
        this.onChangeAddQuantity(ev);

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
    },

    _onChangeMainProductQuantity: function (ev){
        var $quantity = $(ev.currentTarget);
        var $modal = $quantity.parents('.oe_optional_products_modal');
        var product_id = $modal.find('span.oe_price[data-product-id]').first().data('product-id');
        var product_ids = [product_id];
        var $products_dom = [];
        $modal.find("ul.js_add_cart_variants[data-attribute_value_ids]").each(function () {
            var $el = $(this);
            $products_dom.push($el);
            _.each($el.data("attribute_value_ids"), function (values) {
                product_ids.push(values[0]);
            });
        });

        this.triggerVariantChange($modal);
    }
});

return OptionalProductsModal;

});