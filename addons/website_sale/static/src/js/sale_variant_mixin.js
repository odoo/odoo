import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { memoize, uniqueId } from "@web/core/utils/functions";
import { insertThousandsSep } from "@web/core/utils/numbers";
import { throttleForAnimation } from "@web/core/utils/timing";

var VariantMixin = {
    events: {
        'change .css_attribute_color input': '_onChangeColorAttribute',
        'click .o_variant_pills': '_onChangePillsAttribute',
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * When a variant is changed, this will check:
     * - If the selected combination is available or not
     * - The extra price if applicable
     * - The display name of the product ("Customizable desk (White, Steel)")
     * - The new total price
     * - The need of adding a "custom value" input
     *   If the custom value is the only available value
     *   (defined by its data 'is_single_and_custom'),
     *   the custom value will have it's own input & label
     *
     * 'change' events triggered by the user entered custom values are ignored since they
     * are not relevant
     *
     * @param {MouseEvent} ev
     */
    onChangeVariant: function (ev) {
        var $parent = $(ev.target).closest('.js_product');
        if (!$parent.data('uniqueId')) {
            $parent.data('uniqueId', uniqueId());
        }
        this._throttledGetCombinationInfo(this, $parent.data('uniqueId'))(ev);
    },
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {Event} ev
     * @returns {Deferred}
     */
    _getCombinationInfo: function (ev) {
        if ($(ev.target).hasClass('variant_custom_value')) {
            return Promise.resolve();
        }

        const $parent = $(ev.target).closest('.js_product');
        if(!$parent.length){
            return Promise.resolve();
        }
        const combination = this.getSelectedVariantValues($parent);

        return rpc('/website_sale/get_combination_info', {
            'product_template_id': parseInt($parent.find('.product_template_id').val()),
            'product_id': this._getProductId($parent),
            'combination': combination,
            'add_qty': parseInt($parent.find('input[name="add_qty"]').val()),
            'uom_id': this._getUoMId($parent[0]),
            'context': this.context,
            ...this._getOptionalCombinationInfoParam($parent),
        }).then((combinationData) => {
            if (this._shouldIgnoreRpcResult()) {
                return;
            }
            this._onChangeCombination(ev, $parent, combinationData);
            this._checkExclusions($parent, combination);
        });
    },

    _getUoMId: function (element) {
        return parseInt(element.querySelector('input[name="uom_id"]:checked')?.value)
    },

    /**
     * Hook to add optional info to the combination info call.
     *
     * @param {$.Element} $product
     */
    _getOptionalCombinationInfoParam($product) {
        return {};
    },

    /**
     * Will add the "custom value" input for this attribute value if
     * the attribute value is configured as "custom" (see product_attribute_value.is_custom)
     *
     * @private
     * @param {MouseEvent} ev
     */
    handleCustomValues: function ($target) {
        var $variantContainer;
        var $customInput = false;
        if ($target.is('input[type=radio]') && $target.is(':checked')) {
            $variantContainer = $target.closest('ul').closest('li');
            $customInput = $target;
        } else if ($target.is('select')) {
            $variantContainer = $target.closest('li');
            $customInput = $target
                .find('option[value="' + $target.val() + '"]');
        }

        if ($variantContainer) {
            if ($customInput && $customInput.data('is_custom') === 'True') {
                var attributeValueId = $customInput.data('value_id');
                var attributeValueName = $customInput.data('value_name');

                if ($variantContainer.find('.variant_custom_value').length === 0
                    || $variantContainer
                        .find('.variant_custom_value')
                        .data('custom_product_template_attribute_value_id') !== parseInt(
                            attributeValueId
                        )
                ) {
                    $variantContainer.find('.variant_custom_value').remove();

                    const previousCustomValue = $customInput.attr("previous_custom_value");
                    var $input = $('<input>', {
                        type: 'text',
                        'data-custom_product_template_attribute_value_id': attributeValueId,
                        class: 'variant_custom_value form-control mt-2'
                    });

                    $input.attr('placeholder', attributeValueName);
                    $input.addClass('custom_value_radio');
                    $variantContainer.append($input);
                    if (previousCustomValue) {
                        $input.val(previousCustomValue);
                    }
                }
            } else {
                $variantContainer.find('.variant_custom_value').remove();
            }
        }
    },

    /**
     * Triggers the price computation and other variant specific changes
     *
     * @param {$.Element} $container
     */
    triggerVariantChange: function ($container) {
        $container.find('ul[data-attribute_exclusions]').trigger('change');
        $container.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
            VariantMixin.handleCustomValues($(this));
        });
    },

    /**
     * Will return the list of selected product.template.attribute.value ids
     *
     * @param {$.Element} $container the container to look into
     */
    getSelectedVariantValues: function ($container) {
        var values = [];

        var variantsValuesSelectors = [
            'input.js_variant_change:checked',
            'select.js_variant_change'
        ];
        $container.find(variantsValuesSelectors.join(', ')).toArray().forEach((el) => {
            values.push(+$(el).val());
        });

        return values;
    },

    /**
     * Will return a promise:
     *
     * - If the product already exists, immediately resolves it with the product_id
     * - If the product does not exist yet ("dynamic" variant creation), this method will
     *   create the product first and then resolve the promise with the created product's id
     *
     * @param {$.Element} $container the container to look into
     * @param {integer} productId the product id
     * @param {integer} productTemplateId the corresponding product template id
     * @returns {Promise} the promise that will be resolved with a {integer} productId
     */
    selectOrCreateProduct: function ($container, productId, productTemplateId) {
        productId = parseInt(productId);
        productTemplateId = parseInt(productTemplateId);
        var productReady = Promise.resolve();
        if (productId) {
            productReady = Promise.resolve(productId);
        } else {
            var params = {
                product_template_id: productTemplateId,
                product_template_attribute_value_ids:
                    JSON.stringify(VariantMixin.getSelectedVariantValues($container)),
            };

            var route = '/sale/create_product_variant';
            productReady = rpc(route, params);
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

        $parent
            .find('option, input, label, .o_variant_pills')
            .removeClass('css_not_available')
            .not(`#rental_product_start_date, #rental_product_end_date`)
            .removeAttr('disabled')
            .end()
            .filter('option, input')
            .closest('li')
            .removeAttr('title')
            .data('excluded-by', '');

        // exclusion rules: array of ptav
        // for each of them, contains array with the other ptav they exclude
        if (combinationData.exclusions) {
            // browse all the currently selected attributes
            Object.values(combination).forEach((current_ptav) => {
                if (combinationData.exclusions.hasOwnProperty(current_ptav)) {
                    // for each exclusion of the current attribute:
                    Object.values(combinationData.exclusions[current_ptav]).forEach((excluded_ptav) => {
                        // disable the excluded input (even when not already selected)
                        // to give a visual feedback before click
                        self._disableInput(
                            $parent,
                            excluded_ptav,
                            current_ptav,
                            combinationData.mapped_attribute_names
                        );
                    });
                }
            });
        }
        // combination exclusions: array of array of ptav
        // for example a product with 3 variation and one specific variation is disabled (archived)
        //  requires the first 2 to be selected for the third to be disabled
        if (combinationData.archived_combinations) {
            combinationData.archived_combinations.forEach((excludedCombination) => {
                const ptavCommon = excludedCombination.filter((ptav) => combination.includes(ptav));
                if (
                    !!ptavCommon
                    && (combination.length === excludedCombination.length)
                    && (ptavCommon.length === combination.length)
                ) {
                    // Selected combination is archived, all attributes must be disabled from each other
                    combination.forEach((ptav) => {
                        combination.forEach((ptavOther) => {
                            if (ptav === ptavOther) {
                                return;
                            }
                            self._disableInput(
                                $parent,
                                ptav,
                                ptavOther,
                                combinationData.mapped_attribute_names,
                            );
                        })
                    })
                } else if (
                    !!ptavCommon
                    && (combination.length === excludedCombination.length)
                    && (ptavCommon.length === (combination.length - 1))
                ) {
                    // In this case we only need to disable the remaining ptav
                    const disabledPtav = excludedCombination.find((ptav) => !combination.includes(ptav));
                    excludedCombination.forEach((ptav) => {
                        if (ptav === disabledPtav) {
                            return;
                        }
                        self._disableInput(
                            $parent,
                            disabledPtav,
                            ptav,
                            combinationData.mapped_attribute_names,
                        )
                    });
                }
            });
        }
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
     * It will also display a message explaining why the input is not selectable.
     * Based on the "excludedBy" and the "productName" params.
     * e.g: Not available with Color: Black
     *
     * @private
     * @param {$.Element} $parent
     * @param {integer} attributeValueId
     * @param {integer} excludedBy The attribute value that excludes this input
     * @param {Object} attributeNames A dict containing all the names of the attribute values
     *   to show a human readable message explaining why the input is disabled.
     * @param {string} [productName] The parent product. If provided, it will be appended before
     *   the name of the attribute value that excludes this input
     *   e.g: Not available with Customizable Desk (Color: Black)
     */
    _disableInput: function ($parent, attributeValueId, excludedBy, attributeNames, productName) {
        var $input = $parent
            .find('option[value=' + attributeValueId + '], input[value=' + attributeValueId + ']');
        $input.addClass('css_not_available').prop('disabled', true);
        $input.closest('label').addClass('css_not_available');
        $input.closest('.o_variant_pills').addClass('css_not_available');

        const $li = $input.closest('li');

        if (excludedBy && attributeNames) {
            var excludedByData = [];
            if ($li.data('excluded-by')) {
                excludedByData = $li.data('excluded-by');
            }

            var excludedByName = attributeNames[excludedBy];
            if (productName) {
                excludedByName = productName + ' (' + excludedByName + ')';
            }
            excludedByData.push(excludedByName);

            $li.attr('title', _t('Not available with %s', excludedByData.join(', ')));
            $li.data('excluded-by', excludedByData);
        }
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
        const isCombinationPossible = !!combination.is_combination_possible;
        const $pricePerUom = $parent.find(".o_base_unit_price:first .oe_currency_value");
        if ($pricePerUom.length) {
            if (isCombinationPossible && combination.base_unit_price != 0) {
                $pricePerUom.parents(".o_base_unit_price_wrapper").removeClass("d-none");
                $pricePerUom.text(this._priceToStr(combination.base_unit_price));
                $parent.find(".oe_custom_base_unit:first").text(combination.base_unit_name);
            } else {
                $pricePerUom.parents(".o_base_unit_price_wrapper").addClass("d-none");
            }
        }

        // Triggers a new JS event with the correct payload, which is then handled
        // by the google analytics tracking code.
        // Indeed, every time another variant is selected, a new view_item event
        // needs to be tracked by google analytics.
        if ('product_tracking_info' in combination) {
            const $product = $('#product_detail');
            $product.data('product-tracking-info', combination['product_tracking_info']);
            $product.trigger('view_item_event', combination['product_tracking_info']);
        }
        const addToCart = $parent.find('#add_to_cart_wrap');
        const contactUsButton = $parent.parents('#product_details').find('#contact_us_wrapper');
        const productPrice = $parent.find('.product_price');
        const quantity = $parent.find('.css_quantity');
        const product_unavailable = $parent.find('#product_unavailable');
        if (combination.prevent_zero_price_sale) {
            productPrice.removeClass('d-inline-block').addClass('d-none');
            quantity.removeClass('d-inline-flex').addClass('d-none');
            addToCart.removeClass('d-inline-flex').addClass('d-none');
            contactUsButton.removeClass('d-none').addClass('d-flex');
            product_unavailable.removeClass('d-none').addClass('d-flex');
        } else {
            productPrice.removeClass('d-none').addClass('d-inline-block');
            quantity.removeClass('d-none').addClass('d-inline-flex');
            addToCart.removeClass('d-none').addClass('d-inline-flex');
            contactUsButton.removeClass('d-flex').addClass('d-none');
            product_unavailable.removeClass('d-flex').addClass('d-none');
        }
        const url = contactUsButton.find('a').attr('data-url');
        contactUsButton.find('a').attr('href', `${url}?subject=${combination.display_name}`);

        const self = this;
        const $price = $parent.find(".oe_price:first .oe_currency_value");
        const $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        const $compare_price = $parent.find(".oe_compare_list_price")
        $price.text(self._priceToStr(combination.price));
        $default_price.text(self._priceToStr(combination.list_price));

        this._toggleDisable($parent, isCombinationPossible);

        if (combination.has_discounted_price) {
            $default_price
                .closest('.oe_website_sale')
                .addClass("discount");
            $default_price.parent().removeClass('d-none');
            $compare_price.addClass("d-none");
        } else {
            $default_price
                .closest('.oe_website_sale')
                .removeClass("discount");
            $default_price.parent().addClass('d-none');
            $compare_price.removeClass("d-none");
        }

        // update images & tags only when changing product
        // or when either ids are 'false', meaning dynamic products.
        // Dynamic products don't have images BUT they may have invalid
        // combinations that need to disable the image.
        if (!combination.no_product_change) {
            const rootComponentSelectors = ['tr.js_product', '.oe_website_sale'];
            self._updateProductImage(
                $parent.closest(rootComponentSelectors.join(', ')),
                combination.display_image,
                combination.product_id,
                combination.product_template_id,
                combination.carousel,
            );
            $parent
                .find('.o_product_tags:first')
                .replaceWith(combination.product_tags);
        }

        $parent
            .find('.product_id')
            .first()
            .val(combination.product_id || 0)
            .trigger('change');

        this.handleCustomValues($(ev.target));
    },

    /**
     * returns the formatted price
     *
     * @private
     * @param {float} price
     */
    _priceToStr: function (price) {
        var precision = 2;

        if ($('.decimal_precision').length) {
            precision = parseInt($('.decimal_precision').last().data('precision'));
        }
        var formatted = price.toFixed(precision).split(".");
        const { thousandsSep, decimalPoint, grouping } = localization;
        formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
        return formatted.join(decimalPoint);
    },
    /**
     * Returns a throttled `_getCombinationInfo` with a leading and a trailing
     * call, which is memoized per `uniqueId`, and for which previous results
     * are dropped.
     *
     * The uniqueId is needed because on the configurator modal there might be
     * multiple elements triggering the rpc at the same time, and we need each
     * individual product rpc to be executed, but only once per individual
     * product.
     *
     * The leading execution is to keep good reactivity on the first call, for
     * a better user experience. The trailing is because ultimately only the
     * information about the last selected combination is useful. All
     * intermediary rpc can be ignored and are therefore best not done at all.
     *
     * The keepLast is to make sure we only consider the result of the last call, when several
     * (asynchronous) calls are done in parallel.
     *
     * @private
     * @param {string} uniqueId
     * @returns {function}
     */
    _throttledGetCombinationInfo: memoize(function (self, uniqueId) {
        const keepLast = new KeepLast();
        var _getCombinationInfo = throttleForAnimation(self._getCombinationInfo.bind(self));
        return (ev, params) => keepLast.add(_getCombinationInfo(ev, params));
    }),
    /**
     * Toggles the disabled class depending on the $parent element
     * and the possibility of the current combination.
     *
     * @private
     * @param {$.Element} $parent
     * @param {boolean} isCombinationPossible
     */
    _toggleDisable: function ($parent, isCombinationPossible) {
        $parent.toggleClass('css_not_available', !isCombinationPossible);
    },
    /**
     * Updates the product image.
     * This will use the productId if available or will fallback to the productTemplateId.
     *
     * @private
     * @param {$.Element} $productContainer
     * @param {boolean} displayImage will hide the image if true. It will use the 'invisible' class
     *   instead of d-none to prevent layout change
     * @param {integer} product_id
     * @param {integer} productTemplateId
     */
    _updateProductImage: function ($productContainer, displayImage, productId, productTemplateId) {
        var model = productId ? 'product.product' : 'product.template';
        var modelId = productId || productTemplateId;
        var imageUrl = '/web/image/{0}/{1}/' + (this._productImageField ? this._productImageField : 'image_1024');
        var imageSrc = imageUrl
            .replace("{0}", model)
            .replace("{1}", modelId);

        var imagesSelectors = [
            'span[data-oe-model^="product."][data-oe-type="image"] img:first',
            'img.product_detail_img',
        ];

        var $img = $productContainer.find(imagesSelectors.join(', '));

        if (displayImage) {
            $img.removeClass('invisible').attr('src', imageSrc);
        } else {
            $img.addClass('invisible');
        }
    },

    /**
     * Highlight selected color
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeColorAttribute: function (ev) {
        let $eventTarget = $(ev.target);
        var $parent = $eventTarget.closest('.js_product');
        $parent.find('.css_attribute_color')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
        let $attrValueEl = $eventTarget.closest('.variant_attribute').find('.attribute_value')[0];
        if ($attrValueEl) {
            $attrValueEl.innerText = $eventTarget.data('value_name');
        }
    },

    _onChangePillsAttribute: function (ev) {
        const radio = ev.target.closest('.o_variant_pills').querySelector("input");
        radio.click();  // Trigger onChangeVariant.
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.o_variant_pills')
            .removeClass("active border-primary text-primary-emphasis bg-primary-subtle")
            .filter(':has(input:checked)')
            .addClass("active border-primary text-primary-emphasis bg-primary-subtle");
    },

    /**
     * Return true if the current object has been destroyed. Useful to know if
     * the result of a rpc should be handled.
     *
     * @private
     */
    _shouldIgnoreRpcResult() {
        return (typeof this.isDestroyed === "function" && this.isDestroyed());
    },

    /**
     * Extension point for website_sale
     *
     * @private
     * @param {string} uri The uri to adapt
     */
    _getUri: function (uri) {
        return uri;
    }
};

export default VariantMixin;
