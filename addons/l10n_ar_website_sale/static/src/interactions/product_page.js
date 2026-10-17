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
    async _onChangeCombination(ev, parent, combination) {
        await super._onChangeCombination(...arguments);
        this._updatePrice(
            parent,
            '.o_l10n_ar_price_tax_excluded',
            combination.l10n_ar_price_tax_excluded,
            combination.currency_precision
        );
    },
});
