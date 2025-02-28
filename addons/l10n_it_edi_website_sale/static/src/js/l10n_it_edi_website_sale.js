/** @odoo-module **/
import { WebsiteSale } from 'website_sale.website_sale';

WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events, {
        "change input[name='vat'], select[name='country_id']": "computeCodiceFiscale",
    }),

    computeCodiceFiscale: function() {
        const vatValue = this.$('input[name="vat"]').val();
        const countryValue = this.$('select[name="country_id"]').find(':selected').attr('code');
        const l10nItCodiceFiscaleInput = this.$('input[name="l10n_it_codice_fiscale"]');

        if (vatValue && (vatValue.startsWith('IT') || countryValue === 'IT')) {
            if (/^IT[0-9]{11}$/.test(vatValue)) {
                l10nItCodiceFiscaleInput.val(vatValue.slice(2, 13));
            }
            else {
                l10nItCodiceFiscaleInput.val(vatValue);
            }
        }
    },
});
