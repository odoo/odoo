import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * @override
     * Updates the product's excluded price based on the selected variant.
     * Ensuring availability info stays accurate.
     */
    _onChangeCombination(ev, $parent, combination) {
        this._super.apply(this, arguments);
        if ($parent.find('.o_l10n_ar_price_tax_excluded .oe_currency_value').length != 0){
            const $l10n_ar_price_tax_excluded = $parent.find('.o_l10n_ar_price_tax_excluded .oe_currency_value');
            $l10n_ar_price_tax_excluded.text(this._priceToStr(combination.l10n_ar_price_tax_excluded));
        }
    },
})
