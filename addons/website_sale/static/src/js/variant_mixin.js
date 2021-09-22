odoo.define('website_sale.VariantMixin', function (require) {
'use strict';

var VariantMixin = require('sale.VariantMixin');

/**
 * Website behavior is slightly different from backend so we append
 * "_website" to URLs to lead to a different route
 *
 * @private
 * @param {string} uri The uri to adapt
 */
VariantMixin._getUri = function (uri) {
    if (this.isWebsite) {
        return uri + '_website';
    } else {
        return uri;
    }
};
const originalOnChangeCombination = VariantMixin._onChangeCombination;
VariantMixin._onChangeCombination = function (ev, $parent, combination) {
    const $pricePerUom = $parent.find(".o_base_unit_price:first .oe_currency_value");
    if ($pricePerUom) {
        if (combination.is_combination_possible !== false && combination.base_unit_price != 0) {
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

    originalOnChangeCombination.apply(this, [ev, $parent, combination]);
};

const originalToggleDisable = VariantMixin._toggleDisable;
/**
 * Toggles the disabled class depending on the $parent element
 * and the possibility of the current combination. This override
 * allows us to disable the secondary button in the website
 * sale product configuration modal.
 *
 * @private
 * @param {$.Element} $parent
 * @param {boolean} isCombinationPossible
 */
VariantMixin._toggleDisable = function ($parent, isCombinationPossible) {
    if ($parent.hasClass('in_cart')) {
        const secondaryButton = $parent.parents('.modal-content').find('.modal-footer .btn-secondary');
        secondaryButton.prop('disabled', !isCombinationPossible);
        secondaryButton.toggleClass('disabled', !isCombinationPossible);
    }
    originalToggleDisable.apply(this, [$parent, isCombinationPossible]);
};

return VariantMixin;

});
