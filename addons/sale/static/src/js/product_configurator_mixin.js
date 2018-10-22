odoo.define('sale.ProductConfiguratorMixin', function (require) {
'use strict';

var core = require('web.core');
var utils = require('web.utils');
var ajax = require('web.ajax');
var _t = core._t;

var ProductConfiguratorMixin = {
    events: {
        'click .css_attribute_color input': '_onChangeColorAttribute',
        'change .main_product:not(.in_cart) input.js_quantity': 'onChangeAddQuantity',
        'click button.js_add_cart_json': 'onClickAddCartJSON',
        'change [data-attribute_exclusions]': 'onChangeVariant'
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * When a product is added or when the quantity is changed,
     * we need to refresh the total price row
     * TODO awa: add a container context to avoid global selectors ?
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
     *
     * @param {MouseEvent} ev
     */
    onChangeVariant: function (ev) {
        var self = this;

        var $component;
        if ($(ev.currentTarget).closest('form').length > 0){
            $component = $(ev.currentTarget).closest('form');
        } else if ($(ev.currentTarget).closest('.oe_optional_products_modal').length > 0){
            $component = $(ev.currentTarget).closest('.oe_optional_products_modal');
        } else {
            $component = $(ev.currentTarget).closest('.o_product_configurator');
        }
        var qty = $component.find('input[name="add_qty"]').val();

        var $parent = $(ev.target).closest('.js_product');
        var combination = this.getSelectedVariantValues($parent);

        self._checkExclusions($parent, combination);

        ajax.jsonRpc(this._getUri('/product_configurator/get_combination_info'), 'call', {
            product_template_id: parseInt($parent.find('.product_template_id').val()),
            product_id: parseInt($parent.find('.product_id').val()),
            combination: combination,
            add_qty: parseInt(qty),
            pricelist_id: this.pricelistId
        }).then(function (combinationData) {
            self._onChangeCombination(ev, $parent, combinationData);
        });
    },

    /**
     * Will add the "custom value" input for this attribute value if
     * the attribute value is configured as "custom" (see product_attribute_value.is_custom)
     *
     * @private
     * @param {MouseEvent} ev
     */
    handleCustomValues: function ($target){
        var $variantContainer;
        var $customInput = false;
        if ($target.is('input[type=radio]') && $target.is(':checked')) {
            $variantContainer = $target.closest('ul').closest('li');
            $customInput = $target;
        } else if ($target.is('select')){
            $variantContainer = $target.closest('li');
            $customInput = $target
                .find('option[value="' + $target.val() + '"]');
        }

        if ($variantContainer) {
            if ($customInput && $customInput.data('is_custom')) {
                var attributeValueId = $customInput.data('value_id');
                var attributeValueName = $customInput.data('value_name');

                if ($variantContainer.find('.variant_custom_value').length === 0
                        || $variantContainer
                              .find('.variant_custom_value')
                              .data('attribute_value_id') !== parseInt(attributeValueId)){
                    $variantContainer.find('.variant_custom_value_label').remove();
                    $variantContainer.find('.variant_custom_value').remove();

                    var $input = $('<input>', {
                        type: 'text',
                        'data-attribute_value_id': attributeValueId,
                        'data-attribute_value_name': attributeValueName,
                        class: 'variant_custom_value form-control'
                    });

                    var isRadioInput = $target.is('input[type=radio]') &&
                        $target.closest('label.css_attribute_color').length === 0;

                    if (isRadioInput) {
                        $input.addClass('custom_value_radio');
                        $target.closest('div').after($input);
                    } else {
                        var $label = $('<label>', {
                            html: attributeValueName + ': ',
                            class: 'variant_custom_value_label'
                        });
                        $variantContainer.append($label).append($input);
                    }
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
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val() || 0, 10);
        var newQty = quantity > min ? (quantity < max ? quantity : max) : min;

        $input.val(newQty).trigger('change');
        return false;
    },

    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the price list, the price might change when quantity exceeds X
     *
     * @param {MouseEvent} ev
     */
    onChangeAddQuantity: function (ev) {
        var $parent;

        if ($(ev.currentTarget).closest('.oe_optional_products_modal').length > 0){
            $parent = $(ev.currentTarget).closest('.oe_optional_products_modal');
        } else if ($(ev.currentTarget).closest('form').length > 0){
            $parent = $(ev.currentTarget).closest('form');
        }  else {
            $parent = $(ev.currentTarget).closest('.o_product_configurator');
        }

        this.triggerVariantChange($parent);
    },

    /**
     * Triggers the price computation and other variant specific changes
     *
     * @param {$.Element} $container
     */
    triggerVariantChange: function ($container) {
        var self = this;
        $container.find('ul[data-attribute_exclusions]').trigger('change');
        $container.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
            self.handleCustomValues($(this));
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

    /**
     * Will look for attribute values that do not create product variant
     * (see product_attribute.create_variant "dynamic")
     *
     * @param {$.Element} $container
     * @returns {Array} array of attribute values with the following format
     *   {integer} attribute_value_id
     *   {string} attribute_value_name
     *   {integer} value
     *   {string} attribute_name
     *   {boolean} is_custom
     */
    getNoVariantAttributeValues: function ($container) {
        var noVariantAttributeValues = [];
        var variantsValuesSelectors = [
            'input.no_variant.js_variant_change:checked',
            'select.no_variant.js_variant_change'
        ];

        $container.find(variantsValuesSelectors.join(',')).each(function (){
            var $variantValueInput = $(this);

            if ($variantValueInput.is('select')){
                $variantValueInput = $variantValueInput.find('option[value=' + $variantValueInput.val() + ']');
            }

            if ($variantValueInput.length !== 0){
                noVariantAttributeValues.push({
                    'attribute_value_id': $variantValueInput.data('value_id'),
                    'attribute_value_name': $variantValueInput.data('value_name'),
                    'value': $variantValueInput.val(),
                    'attribute_name': $variantValueInput.data('attribute_name'),
                    'is_custom': $variantValueInput.data('is_custom')
                });
            }
        });

        return noVariantAttributeValues;
    },

    /**
     * Will return the list of selected product.template.attribute.value ids
     * For the modal, the "main product"'s attribute values are stored in the
     * "unchanged_value_ids" data
     *
     * @param {$.Element} $container the container to look into
     */
    getSelectedVariantValues: function ($container) {
        var values = [];
        var unchangedValues = $container
            .find('div.oe_unchanged_value_ids')
            .data('unchanged_value_ids') || [];

        var variantsValuesSelectors = [
            'input.js_variant_change:checked',
            'select.js_variant_change'
        ];
        _.each($container.find(variantsValuesSelectors.join(', ')), function (el) {
            values.push(+$(el).val());
        });

        return values.concat(unchangedValues);
    },

    /**
     * Will return a deferred:
     * - If the product already exists, immediately resolves it with the product_id
     * - If the product does not exist yet ("dynamic" variant creation), this method will
     *   create the product first and then resolve the deferred with the created product's id
     *
     * @param {$.Element} $container the container to look into
     * @param {integer} productId the product id
     * @param {integer} productTemplateId the corresponding product template id
     * @param {boolean} useAjax wether the rpc call should be done using ajax.jsonRpc or using _rpc
     * @returns {$.Deferred} the deferred that will be resolved with a {integer} productId
     */
    selectOrCreateProduct: function ($container, productId, productTemplateId, useAjax) {
        var self = this;
        var productReady = $.Deferred();
        if (productId && productId !== '0'){
            productReady.resolve(productId);
        } else {
            var params = {
                model: 'product.template',
                method: 'create_product_variant',
                args: [
                    productTemplateId,
                    JSON.stringify(self.getSelectedVariantValues($container))
                ]
            };

            if (useAjax) {
                productReady = ajax.jsonRpc('/web/dataset/call', 'call', params);
            } else {
                productReady = this._rpc(params);
            }
        }

        return productReady;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Will disable attribute value's inputs based on combination exclusions
     * and will disable the "add" button if the selected combination
     * is not available
     *
     * This will check both the exclusions within the product itself and
     * the exclusions coming from the parent product (meaning that this product
     * is an option of the parent product)
     *
     * It will also check that the selected combination does not exactly
     * match a manually archived product
     *
     * @private
     * @param {$.Element} $parent the parent container to apply exclusions
     * @param {Array} combination the selected combination of product attribute values
     */
    _checkExclusions: function ($parent, combination) {
        var self = this;
        var combinationData = $parent
            .find('ul[data-attribute_exclusions]')
            .data('attribute_exclusions');

        $parent.find('option, input, label').removeClass('css_not_available');

        var disable = false;
        if (combinationData.exclusions) {
            _.each(combination, function (combinationValue){
                if (combinationData.exclusions &&
                    combinationData.exclusions.hasOwnProperty(combinationValue)){
                    // check that the selected combination is in the exclusions
                    _.each(combinationData.exclusions[combinationValue], function (exclusion) {
                        if (!disable && combination.indexOf(exclusion) > -1) {
                            disable = true;
                        }

                        self._disableInput($parent, exclusion);
                    });
                }
            });
        }

        if (combinationData.parent_exclusions){
            _.each(combinationData.parent_exclusions, function (exclusion){
                if (!disable && combination.indexOf(exclusion) > -1) {
                    disable = true;
                }
                self._disableInput($parent, exclusion);
            });
        }

        if (combinationData.archived_combinations){
            _.each(combinationData.archived_combinations, function (archived_combination){
                if (disable) {
                    return;
                }

                disable = _.every(archived_combination, function (attribute_value){
                    return combination.indexOf(attribute_value) > -1;
                });
            });
        }

        $parent.toggleClass('css_not_available', disable);
        $parent.find("#add_to_cart").toggleClass('disabled', disable);
        $parent
            .parents('.modal')
            .find('.o_sale_product_configurator_add')
            .toggleClass('disabled', disable);
    },

    /**
     * Will disable the input/option that refers to the passed attributeValueId.
     * This is used for showing the user that some combinations are not available.
     *
     * @private
     * @param {$.Element} $parent
     * @param {integer} attributeValueId
     */
    _disableInput: function ($parent, attributeValueId) {
        var $input = $parent
            .find('option[value=' + attributeValueId + '], input[value=' + attributeValueId + ']');
        $input.addClass('css_not_available');
        $input.closest('label').addClass('css_not_available');
    },

    /**
     * @see onChangeVariant
     *
     * @private
     * @param {MouseEvent} ev
     * @param {$.Element} $parent
     * @param {Array} combination
     */
    _onChangeCombination: function (ev, $parent, combination) {
        var self = this;
        var $price = $parent.find(".oe_price:first .oe_currency_value");
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
        $price.html(self._priceToStr(combination.price));
        $default_price.html(self._priceToStr(combination.list_price));
        if (combination.list_price - combination.price > 0.01) {
            $default_price
                .closest('.oe_website_sale')
                .addClass("discount");
            $optional_price
                .closest('.oe_optional')
                .removeClass('d-none')
                .css('text-decoration', 'line-through');
            $default_price.parent().removeClass('d-none');
        } else {
            $optional_price.closest('.oe_optional').addClass('d-none');
            $default_price.parent().addClass('d-none');
        }

        var rootComponentSelectors = [
            'tr.js_product',
            '.oe_website_sale',
            '.o_product_configurator'
        ];

        self._updateProductImage(
            $parent.closest(rootComponentSelectors.join(', ')),
            combination.product_id,
            combination.product_template_id
        );

        $parent
            .find('.product_id')
            .first()
            .val(combination.product_id || 0)
            .trigger('change');

        $parent
            .find('.product_display_name')
            .first()
            .val(combination.display_name);

        $parent
            .find('.js_raw_price')
            .first()
            .html(combination.price);

        this.computePriceTotal();
        this.handleCustomValues($(ev.target));
    },

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
     * Updates the product image.
     * This will use the productId if available or will fallback to the productTemplateId.
     *
     * @private
     * @param {$.Element} $productContainer
     * @param {integer} product_id
     * @param {integer} productTemplateId
     */
    _updateProductImage: function ($productContainer, productId, productTemplateId) {
        var $img;
        var model = productId ? 'product.product' : 'product.template';
        var modelId = productId || productTemplateId;
        var imageSrc = '/web/image?model={0}&id={1}&field=image'
            .replace("{0}", model)
            .replace("{1}", modelId);

        if ($productContainer.find('#o-carousel-product').length) {
            $img = $productContainer.find('img.js_variant_img');
            $img.attr("src", imageSrc);
            $img.parent().attr('data-oe-model', model).attr('data-oe-id', modelId)
                .data('oe-model', model).data('oe-id', modelId);

            var $thumbnail = $productContainer.find('img.js_variant_img_small');
            if ($thumbnail.length !== 0) { // if only one, thumbnails are not displayed
                $thumbnail.attr("src", "/web/image/{0}/{1}/image/90x90"
                    .replace('{0}', model)
                    .replace('{1}', modelId));
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
                .attr('data-oe-model', model)
                .attr('data-oe-id', modelId)
                .data('oe-model', model)
                .data('oe-id', modelId);
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
    }
};

return ProductConfiguratorMixin;

});