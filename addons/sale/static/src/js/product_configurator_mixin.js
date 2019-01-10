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
    isSelectedVariantAllowed: true,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * When a product is added or when the quantity is changed,
     * we need to refresh the total price row
     * TODO awa: add a container context to avoid global selectors ?
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
        } else if ($(ev.currentTarget).closest('.o_product_configurator').length > 0) {
            $component = $(ev.currentTarget).closest('.o_product_configurator');
        } else {
            $component = $(ev.currentTarget);
        }
        var qty = $component.find('input[name="add_qty"]').val();

        var $parent = $(ev.target).closest('.js_product');
        var combination = this.getSelectedVariantValues($parent);

        self._checkExclusions($parent, combination);

        ajax.jsonRpc(this._getUri('/product_configurator/get_combination_info'), 'call', {
            product_template_id: parseInt($parent.find('.product_template_id').val()),
            product_id: this._getProductId($parent),
            combination: combination,
            add_qty: parseInt(qty),
            pricelist_id: this.pricelistId || false,
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
     *
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
        productId = parseInt(productId);
        productTemplateId = parseInt(productTemplateId);
        var productReady = $.Deferred();
        if (productId) {
            productReady.resolve(productId);
        } else {
            var params = {
                product_template_id: productTemplateId,
                product_template_attribute_value_ids:
                    JSON.stringify(self.getSelectedVariantValues($container)),
            };

            // Note about 12.0 compatibility: this route will not exist if
            // updating the code but not restarting the server. (404)
            // We don't handle that compatibility because the previous code was
            // not working either: it was making an RPC that failed with any
            // non-admin user anyway. To use this feature, restart the server.
            var route = '/product_configurator/create_product_variant';
            if (useAjax) {
                productReady = ajax.jsonRpc(route, 'call', params);
            } else {
                productReady = this._rpc({route: route, params: params});
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

        function areCombinationsEqual(c1, c2) {
            return c1.length === c2.length && _.every(c1, function (ptav) {
                return c2.indexOf(ptav) > -1;
            });
        }

        function isCombinationInList(c1, list) {
            return _.some(list, function (c2) {
                return areCombinationsEqual(c1, c2);
            });
        }

        function isPtavInCombination(ptav, combination) {
            return combination.indexOf(ptav) > -1;
        }

        var self = this;
        var combinationData = $parent
            .find('ul[data-attribute_exclusions]')
            .data('attribute_exclusions');

        $parent.find('option, input, label').removeClass('css_not_available');

        var disable = false;

        // compatibility 12.0
        var filteredCombination = combination;
        if (combinationData.no_variant_product_template_attribute_value_ids !== undefined) {
            var no_variants = combinationData.no_variant_product_template_attribute_value_ids;
            filteredCombination = _.filter(combination, function (ptav) {
                return !isPtavInCombination(ptav, no_variants);
            });
        }

        // exclusion rules: array of ptav
        // for each of them, contains array with the other ptav they exclude
        if (combinationData.exclusions) {
            // browse all the currently selected attributes
            _.each(combination, function (current_ptav) {
                if (combinationData.exclusions.hasOwnProperty(current_ptav)) {
                    // for each exclusion of the current attribute:
                    _.each(combinationData.exclusions[current_ptav], function (excluded_ptav) {
                        // disable if it excludes any other attribute already in the combination
                        if (isPtavInCombination(excluded_ptav, combination)) {
                            disable = true;
                        }

                        // disable the excluded input (even when not already selected)
                        // to give a visual feedback before click
                        self._disableInput($parent, excluded_ptav);
                    });
                }
            });
        }

        // parent exclusions (tell which attributes are excluded from parent)
        _.each(combinationData.parent_exclusions, function (ptav) {
            if (isPtavInCombination(ptav, combination)) {
                disable = true;
            }
            // disable the excluded input (even when not already selected)
            // to give a visual feedback before click
            self._disableInput($parent, ptav);
        });

        // archived variants
        if (isCombinationInList(filteredCombination, combinationData.archived_combinations)) {
            disable = true;
        }

        // if not using dynamic attributes, exclude variants that are deleted
        if (filteredCombination.length && // compatibility 12.0 list view of variants
            combinationData.has_dynamic_attributes === false &&
            combinationData.existing_combinations !== undefined &&
            !isCombinationInList(filteredCombination, combinationData.existing_combinations)
        ) {
            disable = true;
        }

        this.isSelectedVariantAllowed = !disable;
        $parent.toggleClass('css_not_available', disable);
        $parent.find("#add_to_cart").toggleClass('disabled', disable);
        $parent
            .parents('.modal')
            .find('.o_sale_product_configurator_add')
            .toggleClass('disabled', disable);
    },

    /**
     * Extracted to a method to be extendable by other modules
     *
     * @param {$.Element} $parent
     */
    _getProductId: function ($parent) {
        return parseInt($parent.find('.product_id').val());
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

        // compatibility_check to remove in master
        // needed for fix in 12.0 in the case of git pull and no server restart
        var compatibility_check = combination.list_price - combination.price >= 0.01;
        if (combination.has_discounted_price !== undefined ? combination.has_discounted_price : compatibility_check) {
            $default_price
                .closest('.oe_website_sale')
                .addClass("discount");
            $optional_price
                .closest('.oe_optional')
                .removeClass('d-none')
                .css('text-decoration', 'line-through');
            $default_price.parent().removeClass('d-none');
        } else {
            $default_price
                .closest('.oe_website_sale')
                .removeClass("discount");
            $optional_price.closest('.oe_optional').addClass('d-none');
            $default_price.parent().addClass('d-none');
        }

        var rootComponentSelectors = [
            'tr.js_product',
            '.oe_website_sale',
            '.o_product_configurator'
        ];

        // update images only when changing product
        if (combination.product_id !== this.last_product_id) {
            this.last_product_id = combination.product_id;
            self._updateProductImage(
                $parent.closest(rootComponentSelectors.join(', ')),
                combination.product_id,
                combination.product_template_id,
                combination.carousel
            );
        }

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
        var model = productId ? 'product.product' : 'product.template';
        var modelId = productId || productTemplateId;
        var imageSrc = '/web/image/{0}/{1}/image'
            .replace("{0}", model)
            .replace("{1}", modelId);

        var imagesSelectors = [
            'span[data-oe-model^="product."][data-oe-type="image"] img:first',
            'img.product_detail_img',
            'span.variant_image img'
        ];

        var $img = $productContainer.find(imagesSelectors.join(', '));
        $img.attr('src', imageSrc);
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
     * TODO this should be overriden in website_sale instead.
     *
     * @private
     * @param {string} uri The uri to adapt
     */
    _getUri: function (uri) {
        if (this.isWebsite) {
            return uri + '_website';
        } else {
            return uri;
        }
    }
};

return ProductConfiguratorMixin;

});
