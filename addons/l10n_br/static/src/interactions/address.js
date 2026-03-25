import { patch } from '@web/core/utils/patch';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {

    async willStart() {
        await super.willStart();
        this.setBrFieldsVisibility();
    },

    _selectState(id) {
        this.addressForm.querySelector(
            `select[name="state_id"] > option[value="${id}"]`
        ).selected = 'selected';
    },

    async onChangeZip() {
        await super.onChangeZip();
        if (this._getSelectedCountryCode() !== 'BR') return;

        const cities = this.addressForm.city_id;
        const newZip = this.addressForm.zip.value.padEnd(5, '0');

        for (const option of cities.options) {
            const ranges = option.dataset.l10n_br_zip_ranges;
            if (ranges) {
                // Parse the l10n_br_zip_ranges field (e.g. "[01000-001 05999-999] [08000-000 08499-999]").
                // Loop over each range that is enclosed in [] (e.g. "[01000-001 05999-999]" followed by "[08000-000 08499-999]").
                for (let range of ranges.matchAll(/\[[^[]+]/g)) {
                    // Remove square brackets (after this, range is e.g. "01000-001 05999-999")
                    range = range[0].replace(/[[\]]/g, '');

                    const [start, end] = range.split(' ');

                    // Rely on lexicographical order to figure out if the new zip is in this range.
                    if (newZip >= start && newZip <= end) {
                        cities.dispatchEvent(
                            new CustomEvent('select', { detail: { value: option.value } })
                        );
                        option.selected = 'selected';
                        this._selectState(option.dataset.state_id);
                        return;
                    }
                }
            }
        }
    },

    async onChangeCity() {
        await super.onChangeCity();
        if (this._getSelectedCountryCode() !== 'BR') return;

        const cities = this.addressForm.city_id;
        if (cities.options) {
            this._selectState(cities.selectedOptions[0].dataset.state_id);
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

    async onChangeState() {
        // For BR: don't want the standard behavior of reloading cities based on state
        if (this._getSelectedCountryCode() == 'BR') {
            this.addressForm.city_id.value = "";
            return;
        }
        return await super.onChangeState();
    },

    async onChangeCountry() {
        await this.waitFor(super.onChangeCountry());
        this.setBrFieldsVisibility();
    },

    setBrFieldsVisibility() {
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
