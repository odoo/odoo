import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { CustomerAddress } from '@portal/interactions/address';
import { SelectMenuWrapper } from '@l10n_latam_base/components/select_menu_wrapper/select_menu_wrapper';

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'input[name="zip"]': { 't-on-input': this.onChangeZip.bind(this) },
            '.o_select_city': { 't-on-change': this.onChangeBrazilianCity.bind(this) },
        });

        this.citySelect = this.el.querySelector('select[name="city_id"]');
    },

    async willStart() {
        await this.waitFor(super.willStart());
        if (this.countryCode !== 'BR') return;

        this.mountComponent(
            this.citySelect.parentElement, SelectMenuWrapper, { el: this.citySelect }
        );
        await this._onChangeCountry();
    },

    _selectState(id) {
        this.addressForm.querySelector(
            `select[name="state_id"] > option[value="${id}"]`
        ).selected = 'selected';
    },

    onChangeZip() {
        if (this.countryCode !== 'BR' || this._getSelectedCountryCode() !== 'BR') return;

        const newZip = this.addressForm.zip.value.padEnd(5, '0');

        for (const option of this.addressForm.querySelectorAll('.o_select_city option')) {
            const ranges = option.getAttribute('zip-ranges');
            if (ranges) {
                // Parse the l10n_br_zip_ranges field (e.g. "[01000-001 05999-999] [08000-000 08499-999]").
                // Loop over each range that is enclosed in [] (e.g. "[01000-001 05999-999]" followed by "[08000-000 08499-999]").
                for (let range of ranges.matchAll(/\[[^[]+]/g)) {
                    // Remove square brackets (after this, range is e.g. "01000-001 05999-999")
                    range = range[0].replace(/[[\]]/g, '');

                    const [start, end] = range.split(' ');

                    // Rely on lexicographical order to figure out if the new zip is in this range.
                    if (newZip >= start && newZip <= end) {
                        this.citySelect.dispatchEvent(
                            new CustomEvent('select', { detail: { value: option.value } })
                        );
                        option.selected = 'selected';
                        this._selectState(option.getAttribute('state-id'));
                        return;
                    }
                }
            }
        }
    },

    onChangeBrazilianCity() {
        if (this.countryCode !== 'BR' || this._getSelectedCountryCode() !== 'BR') return;

        if (this.addressForm.city_id.value) {
            this._selectState(
                this.addressForm.city_id
                    .querySelector(`option[value='${this.addressForm.city_id.value}']`)
                    .getAttribute('state-id')
            );
        }
    },

    _setVisibility(selector, should_show) {
        this.addressForm.querySelectorAll(selector).forEach((el) => {
            if (should_show) {
                el.classList.remove('d-none');
            } else {
                el.classList.add('d-none');
            }

            // Disable hidden inputs to avoid sending back e.g. an empty street when street_name and street_number is
            // filled. It causes street_name and street_number to be lost.
            if (el.tagName === 'INPUT') {
                el.disabled = !should_show;
            }

            el.querySelectorAll('input').forEach((input) => (input.disabled = !should_show));
        });
    },

    async _onChangeCountry(init=false) {
        await this.waitFor(super._onChangeCountry(...arguments));
        if (this.countryCode !== 'BR') return;

        if (this._getSelectedCountryCode() === 'BR') {
            this._setVisibility('.o_standard_address', false); // hide
            this._setVisibility('.o_extended_address', true); // show
            this.onChangeZip();
        } else {
            this._setVisibility('.o_standard_address', true); // show
            this._setVisibility('.o_extended_address', false); // hide
        }
    },
});
