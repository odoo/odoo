import VariantMixin from '@website_sale/js/sale_variant_mixin';

const oldOnChangeCombinationStock = VariantMixin._onChangeCombinationStock;

/**
 * Prevent displaying stock values when click and collect is activated.
 *
 * @override of `website_sale_stock`
 */
VariantMixin._onChangeCombinationStock = function (ev, $parent, combination) {
    if (!combination.show_click_and_collect_availability) {
        return oldOnChangeCombinationStock.apply(this, arguments);
    }
}
