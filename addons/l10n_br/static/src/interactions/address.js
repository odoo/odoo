import { patch } from '@web/core/utils/patch';
import { CustomerAddress } from '@portal/interactions/address';
import { _t } from "@web/core/l10n/translation";

patch(CustomerAddress.prototype, {

    setup() {
        // Set main street2 label before updating it
        this.street2LabelText = document.querySelector('label[for="o_street2"]').textContent;
        super.setup();
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

    async onChangeState() {
        // For BR: don't want the standard behavior of reloading cities based on state
        if (this._getSelectedCountryCode() == 'BR') {
            this.addressForm.city_id.value = "";
            return;
        }
        return await super.onChangeState();
    },

    async onChangeCountry() {
        await super.onChangeCountry();
        if (this._getSelectedCountryCode() === 'BR') {
            this._setVisibility('.o_standard_address', false); // hide
            this._setVisibility('.o_extended_address', true); // show
            this.onChangeZip();
        } else {
            this._setVisibility('.o_standard_address', true); // show
            this._setVisibility('.o_extended_address', false); // hide
        }
    },

    _updateAddressLayout() {
        super._updateAddressLayout();
        const street2Label = this.addressForm.querySelector('label[for="o_street2"]');
        street2Label.textContent =
            this._getSelectedCountryCode() === "BR" ? _t("Neighborhood") : this.street2LabelText;
    },

    _setVisibility(selector, shouldShow) {
        const fields = [...this.addressForm.querySelectorAll(selector)].map((field) => field.name);
        fields.forEach((fieldName) => {
            if (shouldShow) {
                this._showInput(fieldName);
            } else {
                this._hideInput(fieldName);
            }
        });
    },
});
