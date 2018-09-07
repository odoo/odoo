odoo.define('sale.ProductConfiguratorMixin', function (require) {
'use strict';

var core = require('web.core');
var utils = require('web.utils');
var ajax = require('web.ajax');
var _t = core._t;

var variantsSelectors = [
    'input.js_variant_change',
    'select.js_variant_change',
    'input.js_product_change',
    '[data-attribute_value_ids]'
];
var variantChangeEvent = 'change ' + variantsSelectors.join(', ');
var events = {
    'click .css_attribute_color input': '_onChangeColorAttribute',
    'change input.js_quantity': 'onChangeAddQuantity',
    'click button.js_add_cart_json': 'onClickAddCartJSON',
};
events[variantChangeEvent] = 'onChangeVariant';

var ProductConfiguratorMixin = {
    events: events,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * When a product is added or when the quantity is changed,
     * we need to refresh the total price row
     * TODO (awa): add a container context to avoid global selectors ?
     *
     */
    computePriceTotal: function () {
        if ($('.js_price_total').length){
            var price = 0;
            $('.js_product.in_cart').each(function (){
                var quantity = parseInt($('input[name="add_qty"]').first().val());
                price += parseFloat($(this).find('.js_raw_price').html()) * quantity;
            });

            $('.js_price_total .oe_currency_value').html(
                this._priceToStr(parseFloat(price))
            );
        }
    },

    /**
     * When a variant is changed, this will check:
     * - If the selected combination is available or not
     * - The extra price if applicable
     * - The display name of the product ("Customizable desk (White, Steel)")
     * - The new total price
     * - The need of adding a "custom value" input
     * TODO (awa): change ugly [0], [1], [2], ... to a dict
     *
     * @param {MouseEvent}
     * @param {string} params.imagesSize "small" or "medium" or ""
     */
    onChangeVariant: function (ev, imagesSize) {
        var self = this;

        var $parent = $(ev.target).closest('.js_product');
        var $ul = $parent.find('.js_add_cart_variants');
        var $product_id = $parent.find('.product_id').first();
        var $product_display_name = $parent.find('.product_display_name').first();
        var $product_raw_price = $parent.find('.js_raw_price').first();
        var $price = $parent.find(".oe_price:first .oe_currency_value");
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
        var variant_ids = $ul.data("attribute_value_ids");
        var values = [];
        var unchanged_values = $parent
            .find('div.oe_unchanged_value_ids')
            .data('unchanged_value_ids') || [];

        var variantsValuesSelectors = [
            'input.js_variant_change:checked',
            'select.js_variant_change'
        ];
        _.each($parent.find(variantsValuesSelectors.join(', ')), function (el) {
            values.push(+$(el).val());
        });
        values = values.concat(unchanged_values);
        var list_variant_id = parseInt($parent.find('input.js_product_change:checked').val());

        $parent.find("label").removeClass('text-muted css_not_available');

        var product_id = false;
        var display_name = false;
        var product_raw_price = false;
        for (var k in variant_ids) {
            if (_.isEmpty(_.difference(variant_ids[k][1], values))
                    || variant_ids[k][0] === list_variant_id) {
                $price.html(self._priceToStr(variant_ids[k][2]));
                $default_price.html(self._priceToStr(variant_ids[k][3]));
                if (variant_ids[k][3]-variant_ids[k][2]>0.01) {
                    $default_price
                        .closest('.oe_website_sale')
                        .addClass("discount");
                    $optional_price
                        .closest('.oe_optional')
                        .show()
                        .css('text-decoration', 'line-through');
                    $default_price.parent().removeClass('d-none');
                } else {
                    $optional_price.closest('.oe_optional').hide();
                    $default_price.parent().addClass('d-none');
                }
                product_id = variant_ids[k][0];
                product_raw_price = variant_ids[k][2];
                display_name = variant_ids[k][4];
                var rootComponentSelectors = [
                    'tr.js_product',
                    '.oe_website_sale',
                    '.o_product_configurator'
                ];
                self._updateProductImage(
                    $(ev.currentTarget).closest(rootComponentSelectors.join(', ')),
                    product_id,
                    imagesSize);
                break;
            }
        }

        var variantsSelectors = [
            'input.js_variant_change:radio',
            'select.js_variant_change'
        ];

        _.each($parent.find(variantsSelectors.join(', ')), function (elem) {
            var $input = $(elem);
            var id = +$input.val();
            var values = [id];

            variantsValuesSelectors = ['select.js_variant_change'];
            var checkedVariantSelector = "ul:not(:has(input.js_variant_change[value='" + id + "']))";
            checkedVariantSelector += " input.js_variant_change:checked";
            variantsValuesSelectors.unshift(checkedVariantSelector);

            _.each($parent.find(variantsValuesSelectors.join(', ')), function (elem) {
                values.push(+$(elem).val());
            });

            for (var k in variant_ids) {
                if (!_.difference(values, variant_ids[k][1]).length) {
                    return;
                }
            }
            $input.closest("label").addClass("css_not_available");
            $input.find("option[value='" + id + "']").addClass("css_not_available");
        });

        if (product_id) {
            $parent.removeClass("css_not_available");
            $product_id.val(product_id);
            $product_display_name.val(display_name);
            $product_raw_price.html(product_raw_price);
            $parent
                .parents('.modal')
                .find('.o_sale_product_configurator_add')
                .removeClass("disabled");

            var $add_to_cart_button = $parent.find("#add_to_cart");
            if (!$add_to_cart_button.hasClass('out_of_stock')) {
                $add_to_cart_button.removeClass("disabled");
            }
        } else {
            $parent.addClass("css_not_available");
            $product_id.val(0);
            $product_display_name.val('');
            $parent.find("#add_to_cart").addClass("disabled");
            $parent
                .parents('.modal')
                .find('.o_sale_product_configurator_add')
                .addClass("disabled");
        }

        this.computePriceTotal();
        this.handleCustomValues(ev);
    },

    /**
     * Will add the "custom value" input for this attribute value if necessary
     *
     * @private
     * @param {MouseEvent} ev
     */
    handleCustomValues: function (ev){
        var $variantContainer;
        var addCustomValueField = false;
        var attributeValueId = false;
        var attributeValueName = false;
        if ($(ev.target).is('input[type=radio]') && $(ev.target).is(':checked')) {
            $variantContainer = $(ev.target).closest('ul').closest('li');
            addCustomValueField = $(ev.target).data('is_custom');
            attributeValueId = $(ev.target).data('value_id');
            attributeValueName = $(ev.target).data('value_name');
        } else if ($(ev.target).is('select')){
            $variantContainer = $(ev.target).closest('li');
            var $selectedOption = $(ev.target)
                .find('option[value="' + $(ev.target).val() + '"]');
            addCustomValueField = $selectedOption.data('is_custom');
            attributeValueId = $selectedOption.data('value_id');
            attributeValueName = $selectedOption.data('value_name');
        }

        if ($variantContainer) {
            if (addCustomValueField && attributeValueId && attributeValueName) {
                if ($variantContainer.find('.variant_custom_value').length === 0
                        || $variantContainer
                              .find('.variant_custom_value')
                              .data('attribute_value_id') !== parseInt(attributeValueId)){
                    $variantContainer.find('.variant_custom_value_label').remove();
                    $variantContainer.find('.variant_custom_value').remove();

                    var $label = $('<label>', {
                        html: attributeValueName + ': ',
                        class: 'variant_custom_value_label'
                    });

                    var $input = $('<input>', {
                        type: 'text',
                        'data-attribute_value_id': attributeValueId,
                        'data-attribute_value_name': attributeValueName,
                        class: 'variant_custom_value form-control'
                    });
                    $variantContainer.append($label).append($input);
                }
            } else {
                $variantContainer.find('.variant_custom_value_label').remove();
                $variantContainer.find('.variant_custom_value').remove();
            }
        }
    },

    /**
     * Hack to add and remove from cart with json
     *
     * @param {MouseEvent} ev
     */
    onClickAddCartJSON: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.closest('.input-group').find("input");
        var product_id = +$input
            .closest('*:has(input[name="product_id"])')
            .find('input[name="product_id"]')
            .val();
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val() || 0, 10);
        var new_qty = quantity > min ? (quantity < max ? quantity : max) : min;
        // if they are more of one input for this product (eg: option modal)
        $('input[name="'+$input.attr("name")+'"]').add($input).filter(function () {
            var $prod = $(this).closest('*:has(input[name="product_id"])');
            return !$prod.length || +$prod.find('input[name="product_id"]').val() === product_id;
        }).val(new_qty).trigger('change', [false]);
        return false;
    },

    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the price list, the price might change when quantity exceeds X
     *
     * @param {MouseEvent} ev
     */
    onChangeAddQuantity: function (ev, noStockCheck) {
        var self = this;
        var $parent;
        if ($(ev.currentTarget).closest('form').length > 0){
            $parent = $(ev.currentTarget).closest('form');
        } else if ($(ev.currentTarget).closest('.oe_optional_products_modal').length > 0){
            $parent = $(ev.currentTarget).closest('.oe_optional_products_modal');
        } else {
            $parent = $(ev.currentTarget).closest('.o_product_configurator');
        }

        var qty = $parent.find('input[name="add_qty"]').val();
        var productIDs = [];
        $parent.find(".js_product .js_add_cart_variants").each(function () {
            _.each($(this).data("attribute_value_ids"), function (entry){
                productIDs.push(entry[0]);
            });
        });

        var getPriceUrl = '/product_configurator/get_unit_price' + (this.isWebsite ? '_website' : '');
        if (productIDs.length) {
            ajax.jsonRpc(getPriceUrl, 'call', {
                product_ids: productIDs,
                add_qty: parseInt(qty),
                pricelist_id: this.pricelistId
            }).then(function (data) {
                $parent.find(".js_product .js_add_cart_variants").each(function () {
                    var currentAttributesData = $(this).data("attribute_value_ids");
                    for (var j = 0 ; j < currentAttributesData.length ; j++) {
                        // update the price of the product (index "2") based on its id (index "0")
                        currentAttributesData[j][2] = data[currentAttributesData[j][0]];
                    }
                    $(this).trigger('change', [noStockCheck]);

                    self.computePriceTotal();
                });
            });
        }
    },

    /**
     * Triggers the price computation and other variant specific changes
     *
     * @param {$.Element} $container
     */
    triggerVariantChange: function ($container) {
        $container.find('.js_add_cart_variants li[data-attribute_id]').each(function () {
            $(this)
                .find('input.js_variant_change, select.js_variant_change')
                .first()
                .trigger('change');
        });
    },

    /**
     * Will look for user custom attribute values
     * in the provided container
     *
     * @param {$.Element} $container
     * @returns {Array} array of custom values with the following format
     *   {integer} attribute_value_id
     *   {string} attribute_value_name
     *   {string} custom_value
     */
    getCustomVariantValues: function ($container) {
        var variantCustomValues = [];
        $container.find('.variant_custom_value').each(function (){
            var $variantCustomValueInput = $(this);
            if ($variantCustomValueInput.length !== 0){
                variantCustomValues.push({
                    'attribute_value_id': $variantCustomValueInput.data('attribute_value_id'),
                    'attribute_value_name': $variantCustomValueInput.data('attribute_value_name'),
                    'custom_value': $variantCustomValueInput.val(),
                });
            }
        });

        return variantCustomValues;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * returns the formatted price
     *
     * @private
     * @param {float} price
     */
    _priceToStr: function (price) {
        var l10n = _t.database.parameters;
        var precision = 2;

        if ($('.decimal_precision').length) {
            precision = parseInt($('.decimal_precision').last().data('precision'));
        }
        var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
        formatted[0] = utils.insert_thousand_seps(formatted[0]);
        return formatted.join(l10n.decimal_point);
    },

    /**
     * Updates the product image
     *
     * @private
     * @param {$.Element} $productContainer
     * @param {integer} product_id
     * @param {string} imagesSize
     */
    _updateProductImage: function ($productContainer, product_id, imagesSize) {
        var $img;
        var imageSrc = '/web/image?model=product.product&id={0}&field={1}'
            .replace("{0}", product_id)
            .replace("{1}", _.isEmpty(imagesSize) ? 'image' : ('image_' + imagesSize));

        if ($productContainer.find('#o-carousel-product').length) {
            $img = $productContainer.find('img.js_variant_img');
            $img.attr("src", imageSrc);
            $img.parent().attr('data-oe-model', 'product.product').attr('data-oe-id', product_id)
                .data('oe-model', 'product.product').data('oe-id', product_id);

            var $thumbnail = $productContainer.find('img.js_variant_img_small');
            if ($thumbnail.length !== 0) { // if only one, thumbnails are not displayed
                $thumbnail.attr("src", "/web/image/product.product/" + product_id + "/image/90x90");
                $('.carousel').carousel(0);
            }
        }
        else {
            var imagesSelectors = [
                'span[data-oe-model^="product."][data-oe-type="image"] img:first',
                'img.product_detail_img',
                'span.variant_image img'
            ];

            $img = $productContainer.find(imagesSelectors.join(', '));
            $img.attr('src', imageSrc);
            $img.parent()
                .attr('data-oe-model', 'product.product')
                .attr('data-oe-id', product_id)
                .data('oe-model', 'product.product')
                .data('oe-id', product_id);
        }
        // reset zooming constructs
        $img.filter('[data-zoom-image]').attr('data-zoom-image', $img.attr('src'));
        if ($img.data('zoomOdoo') !== undefined) {
            $img.data('zoomOdoo').isReady = false;
        }
    },

    /**
     * Highlight selected color
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeColorAttribute: function (ev) {
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.css_attribute_color')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
    }
};

return ProductConfiguratorMixin;

});