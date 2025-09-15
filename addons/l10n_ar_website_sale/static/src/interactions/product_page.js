import { patch } from '@web/core/utils/patch';
import { ProductPage } from '@website_sale/interactions/product_page';

patch(ProductPage.prototype, {
    /**
     * Override of `website_sale` to update the product's tax excluded price based on the selected
     * variant.
     *
     * @param {Event} ev
     * @param {Element} parent
     * @param {Object} combination
     */
    _onChangeCombination(ev, parent, combination) {
        super._onChangeCombination(...arguments);
        const currencyValue = parent.querySelector(
            '.o_l10n_ar_price_tax_excluded .oe_currency_value'
        );
        if (currencyValue) {
            currencyValue.textContent = this._priceToStr(combination.l10n_ar_price_tax_excluded);
        }
    },
});
