import customerAddress from "@portal/js/address";
import { attachComponent } from "@web_editor/js/core/owl_utils";
import { SelectMenuWrapper } from "@l10n_latam_base/components/select_menu_wrapper/select_menu_wrapper";

customerAddress.include({
    events: Object.assign({}, customerAddress.prototype.events, {
        'input input[name="zip"]': "_onChangeZip",
        "change .o_select_city": "_onChangeBrazilianCity",
    }),

    start: async function () {
        this._super.apply(this, arguments);

        if (this.countryCode === "BR") {
            const selectEl = this.el.querySelector("select[name='city_id']");
            this.selectMenuWrapper = await attachComponent(
                this,
                selectEl.parentElement,
                SelectMenuWrapper,
                {
                    el: selectEl,
                }
            );
            await this._changeCountry();
        }
    },

    _selectedCountryCode: function() {
        const countryOption = this.addressForm.country_id;
        return countryOption.selectedOptions[0].getAttribute("code");
    },

    _selectState: function (id) {
        this.addressForm.querySelector(`select[name="state_id"] > option[value="${id}"]`).selected =
            "selected";
    },

    _onChangeZip: function () {
        if (this.countryCode !== "BR" || this._selectedCountryCode() !== "BR") {
            return;
        }

        const newZip = this.addressForm.zip.value.padEnd(5, "0");

        for (const option of this.addressForm.querySelectorAll(".o_select_city option")) {
            const ranges = option.getAttribute("zip-ranges");
            if (ranges) {
                // Parse the l10n_br_zip_ranges field (e.g. "[01000-001 05999-999] [08000-000 08499-999]").
                // Loop over each range that is enclosed in [] (e.g. "[01000-001 05999-999]" followed by "[08000-000 08499-999]").
                for (let range of ranges.matchAll(/\[[^[]+]/g)) {
                    // Remove square brackets (after this, range is e.g. "01000-001 05999-999")
                    range = range[0].replace(/[[\]]/g, "");

                    const [start, end] = range.split(" ");

                    // Rely on lexicographical order to figure out if the new zip is in this range.
                    if (newZip >= start && newZip <= end) {
                        if (this.selectMenuWrapper) {
                            this.selectMenuWrapper.component.onSelect(option.value);
                        }
                        option.selected = "selected";
                        this._selectState(option.getAttribute("state-id"));
                        return;
                    }
                }
            }
        }
    },

    _onChangeBrazilianCity: function () {
        if (this.countryCode !== "BR" || this._selectedCountryCode() !== "BR") {
            return;
        }

        if (this.addressForm.city_id.value) {
            this._selectState(
                this.addressForm.city_id
                    .querySelector(`option[value='${this.addressForm.city_id.value}']`)
                    .getAttribute("state-id")
            );
        }
    },

    _setVisibility(selector, should_show) {
        this.addressForm.querySelectorAll(selector).forEach((el) => {
            if (should_show) {
                el.classList.remove("d-none");
            } else {
                el.classList.add("d-none");
            }

            // Disable hidden inputs to avoid sending back e.g. an empty street when street_name and street_number is
            // filled. It causes street_name and street_number to be lost.
            if (el.tagName === "INPUT") {
                el.disabled = !should_show;
            }

            el.querySelectorAll("input").forEach((input) => (input.disabled = !should_show));
        });
    },

    async _changeCountry(ev) {
        const res = await this._super(...arguments);
        if (this.countryCode !== "BR") {
            return res;
        }

        if (this._selectedCountryCode() === "BR") {
            this._setVisibility(".o_standard_address", false); // hide
            this._setVisibility(".o_extended_address", true); // show
            this._onChangeZip();
        } else {
            this._setVisibility(".o_standard_address", true); // show
            this._setVisibility(".o_extended_address", false); // hide
        }

        return res;
    },
});
