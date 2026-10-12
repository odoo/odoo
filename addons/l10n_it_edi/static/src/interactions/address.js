import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'input[name="vat"], select[name="country_id"]': {
                't-on-change': this.computeCodiceFiscale.bind(this),
            },
        });
    },

    computeCodiceFiscale() {
        const vat = this.el.querySelector('input[name="vat"]');
        const countryValue = this.el.querySelector('select[name="country_id"]')
            .selectedOptions[0]?.getAttribute('code');
        const l10nItCodiceFiscaleInput = this.el.querySelector('input[name="l10n_it_codice_fiscale"]');

        if (
            l10nItCodiceFiscaleInput
            && vat
            && (vat.value.startsWith('IT') || countryValue === 'IT')
        ) {
            l10nItCodiceFiscaleInput.value = /^IT[0-9]{11}$/.test(vat.value)
                ? vat.value.slice(2, 13) : vat.value;
        }
    },
});
