odoo.define('sale.OptionalProductsModal', function (require) {
    "use strict";

var ajax = require('web.ajax');
var Widget = require('web.Widget');
var ServicesMixin = require('web.ServicesMixin');
var weContext = require('web_editor.context');
var ProductConfiguratorUtils = require('sale.product_configurator_utils');

var product_name_map = {};
var optional_products_map = {};

var OptionalProductsModal = Widget.extend(ServicesMixin, {
    events: _.extend({}, Widget.prototype.events, {
        'click .css_attribute_color input': '_onColorClick',
    }),
    /**
     * @override
     */
    init: function (quantity, product_id, container, pricelistId, isWebsite) {
        this._super.apply(this, arguments);
        this.quantity = quantity;
        this.product_id = product_id;
        this.container = container;
        this.pricelistId = pricelistId;
        this.isWebsite = isWebsite;
    },
     /**
     * @override
     */
    willStart: function () {
        var self = this;

        var getModalContent = ajax.jsonRpc(this._getUri("/product_configurator/show_optional_products"), 'call', {
            product_id: self.product_id,
            pricelist_id: self.pricelistId,
            kwargs: {
                context: _.extend({'quantity': self.quantity}, weContext.get()),
            }
        })
        .then(function (modal_content) {
            self.modal_content = modal_content;
        });

        var parentInit = self._super.apply(self, arguments);
        return $.when(getModalContent, parentInit);
    },
    /**
     * @override
     */
    start: function() {
        this._renderModal();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @public
     * Returns the list of selected products as products[{product_id, quantity}]
     */
    getSelectedProducts: function() {
        var self = this;
        var products = [];
        this.$modal.find('.js_product.in_cart').each(function(){
            var quantity = 0;
            var $item = $(this);
            if($item.find('input[name="add_qty"]').length){
                quantity = $item.find('input[name="add_qty"]').val();
            } else {
                quantity = parseInt($item.find('.optional_product_quantity span.add_qty').html().trim());
            }
            
            products.push({
                product_id: $item.find('input.product_id').length ? $item.find('input.product_id').val() : self.product_id,
                quantity: quantity
            });
        });

        return products;
    },

    // ------------------------------------------
    // Private
    // ------------------------------------------

    _renderModal: function(){
        var self = this;
        if (self.modal_content){
            var $modal = $(self.modal_content);
            $modal.find('img:first').attr("src", "/web/image/product.product/" + self.product_id + "/image_medium");
    
            $modal
                .modal()
                .appendTo(self.container)
                .addClass('oe_optional_products_modal' + (self.isWebsite ? ' oe_website_sale' : ''))
                .on('hidden.bs.modal', function () {
                    $(this).remove();
                })
                .on('shown.bs.modal', function () {
                    self.trigger('modal_ready', $modal);
                });

                self.$modal = $modal;
                self._addModalEvents();
        } else {
            self.trigger('options_empty');
        }
    },

    /**
     * Website behavior is slighlty different from backend so we append "_website" to URLs to lead to a different route
     */
    _getUri: function(uri) {
        if (this.isWebsite){
            return uri + '_website';
        } else {
            return uri;
        }
    },

    _addModalEvents: function() {
        this.$modal.on('click', '.a-submit', {self: this}, this._onSubmit);
        this.$modal.on('click', '.css_attribute_color input', this._onColorClick);
        this.$modal.on("click", 'a.js_add, a.js_remove', {self: this}, this._onAddOrRemoveOption);
        this.$modal.on("change", "input.js_quantity", {self: this}, this._onChangeQuantity);
        this.$modal.on("change", 'input[name="add_qty"]', this._onChangeMainProductQuantity);
        ProductConfiguratorUtils.addConfiguratorEvents(this.$modal, "small", this.isWebsite, this.pricelistId);

        // trigger add_qty change to synchronise quantity with previous window
        this.$modal.find('input[name="add_qty"]').val(this.quantity).change();

        // trigger input change to validate fields and display custom prices
        $('.js_add_cart_variants', this.$modal).each(function () {
            $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
        });
    },

    /**
     * Handles the "Back" and "Confirm" buttons and triggers the according events
     */
    _onSubmit: function(ev){
        var $modal = $(this).parents('.oe_optional_products_modal');
        $modal.modal('hide');
        ev.preventDefault();

        var $a = $(this);
        ev.data.self.trigger($a.hasClass('confirm') ? 'confirm' : 'back');
    },

    /**
     * TODO (awa): check if necessary
     */
    _onColorClick: function(){
        var $modal = $(this).parents('.oe_optional_products_modal');
        $modal.find('.css_attribute_color').removeClass("active");
        $modal.find('.css_attribute_color:has(input:checked)').addClass("active");
    },

    _onAddOrRemoveOption: function(ev){
        ev.preventDefault();
        var $modal = $(this).parents('.oe_optional_products_modal');
        var $select_options_text = $modal.find('.o_select_options');
        var $main_product = $modal.find('.js_product:first');
        var $parent = $(this).parents('.js_product:first');
        $parent.find("a.js_add, span.js_remove").toggleClass('d-none');
        $parent.find("input.js_optional_same_quantity").val( $(this).hasClass("js_add") ? 1 : 0 );
        $parent.find(".js_remove");

        var product_id = $parent.find(".product_template_id").val();
        if ($(this).hasClass('js_add')) {
            // remove attribute values selection and move quantity to the correct table spot (".td-qty"))
            $parent.addClass('in_cart');
            $parent.find('.td-qty').addClass('text-center');
            $parent.find('.td-qty').append($parent.find('.optional_product_quantity'));

            // change product name to display_name (containing attribute values) when it's added to cart
            // the "simple" name is kept into a map to revert to it if the product is removed from the cart
            product_name_map[product_id] = $parent.find(".product-name").html();
            $parent.find(".product-name").html($parent.find(".product_display_name").val());

            // if it's an optional product of an optional product, place it after it's parent
            var parent_product_id = null;
            for (var produt_id_key in optional_products_map) {
                if (optional_products_map[produt_id_key].indexOf(product_id) != -1) {
                    parent_product_id = produt_id_key;
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

            var isWebsite = ev.data.self.isWebsite;
            var pricelistId = ev.data.self.pricelistId;
            var product_variant_id = $parent.find('.product_id').val();
            ajax.jsonRpc(ev.data.self._getUri("/product_configurator/optional_product_items"), 'call', {
                'product_id': product_variant_id,
                'pricelist_id': ev.data.self.pricelistId
            }).then(function (addedItem) {
                var $addedItem = $(addedItem);
                $modal.find('tr:last').after($addedItem);

                ProductConfiguratorUtils.addConfiguratorEvents($addedItem, "small", isWebsite, pricelistId);

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
                
                if($select_options_text.nextAll('.js_product').length === 0){
                    // no more optional products to select -> hide the header
                    $select_options_text.hide();
                }
            });
        } else {
            // restore attribute values selection
            $parent.removeClass('in_cart');
            $parent.find('.td-qty').removeClass('text-center');
            $parent.find('.js_remove.d-none').prepend($parent.find('.optional_product_quantity'));

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

        ProductConfiguratorUtils.computePriceTotal();
    },

    _onChangeQuantity: function(ev){
        var qty = parseFloat($(this).val());
        var $modal = $(this).parents('.oe_optional_products_modal');
        if (qty === 1) {
            $modal.find(".js_items").addClass('d-none').removeClass('add_qty');
            $modal.find(".js_item").removeClass('d-none').addClass('add_qty');
        } else {
            $modal.find(".js_items").removeClass('d-none').addClass('add_qty').text(qty);
            $modal.find(".js_item").addClass('d-none').removeClass('add_qty');
        }
    },

    _onChangeMainProductQuantity: function(){
        var $modal = $(this).parents('.oe_optional_products_modal');
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

        // trigger input change to validate fields and display custom prices
        $('.js_add_cart_variants', $modal).each(function () {
            $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
        });
    }
});
return OptionalProductsModal;
});