/** @odoo-module **/

import websiteSaleAddress from '@website_sale/js/address';

websiteSaleAddress.include({
    events: Object.assign(
        {},
        websiteSaleAddress.prototype.events,
        {
            'input input[name="zip"]': '_onChangeZip',
        }
    ),

    _selectState: function(id) {
        this.addressForm.querySelector(`select[name="state_id"] > option[value="${id}"]`).selected = 'selected';
    },

    _onChangeZip: function() {
        if (this.countryCode !== 'BR') {
            return;
        }

        const newZip = this.addressForm.zip.value.padEnd(5, '0');

        for (let option of this.addressForm.querySelectorAll('select[name="city_id"]:not(.d-none) > option')) {
            const ranges = option.getAttribute('zip-ranges');
            if (ranges) {
                // Parse the l10n_br_zip_ranges field (e.g. "[01000-001 05999-999] [08000-000 08499-999]").
                // Loop over each range that is enclosed in [] (e.g. "[01000-001 05999-999]" followed by "[08000-000 08499-999]").
                for (let range of ranges.matchAll(/\[[^\[]+\]/g)) {
                    // Remove square brackets (after this, range is e.g. "01000-001 05999-999")
                    range = range[0].replace(/[\[\]]/g, '');

                    let [start, end] = range.split(' ');

                    // Rely on lexicographical order to figure out if the new zip is in this range.
                    if (newZip >= start && newZip <= end) {
                        option.selected = 'selected';
                        this._selectState(option.getAttribute('state-id'));
                        return;
                    }
                }
            }
        }
    },

    _setVisibility(selector, should_show) {
        this.addressForm.querySelectorAll(selector).forEach(el => {
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

            el.querySelectorAll('input').forEach(input => input.disabled = !should_show);
        })
    },

    async _changeCountry(ev) {
        const res = await this._super(...arguments);
        if (this.countryCode !== 'BR') {
            return res;
        }

        const countryOption = this.addressForm.country_id;
        const selectedCountryCode = countryOption.value ? countryOption.selectedOptions[0].getAttribute('code') : '';

        if (selectedCountryCode === 'BR') {
            this._setVisibility('.o_standard_address', false); // hide
            this._setVisibility('.o_extended_address', true); // show
            this._onChangeZip();
        } else {
            this._setVisibility('.o_standard_address', true); // show
            this._setVisibility('.o_extended_address', false); // hide
        }

        return res;
    }
});
