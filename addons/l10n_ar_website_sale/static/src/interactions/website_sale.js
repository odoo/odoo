import { patch } from '@web/core/utils/patch';
import { WebsiteSale } from '@website_sale/interactions/website_sale';

patch(WebsiteSale.prototype, {
    /**
     * @override
     * Updates the product's excluded price based on the selected variant.
     * Ensuring availability info stays accurate.
     */
    _onChangeCombination(ev, parent, combination) {
        super._onChangeCombination(...arguments);
        const currencyValue = parent.querySelector(
            '.o_l10n_ar_price_tax_excluded .oe_currency_value'
        );
        if (currencyValue) {
            const { currency_precision, l10n_ar_price_tax_excluded } = combination;
            currencyValue.textContent = this._priceToStr(
                l10n_ar_price_tax_excluded, currency_precision,
            );
        }
    },
})
