/** @odoo-module **/
import websiteSaleAddress from "@website_sale/js/address";
import { Component, useState } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { attachComponent } from "@web_editor/js/core/owl_utils";

class SelectMenuWrapper extends Component {
    static template = "l10n_br_website_sale.SelectMenuWrapper";
    static components = { SelectMenu };
    static props = {
        el: { optional: true, type: Object },
    };

    setup() {
        this.state = useState({
            choices: [],
            value: this.props.el.value,
        });
        this.state.choices = [...this.props.el.querySelectorAll("option")].filter((x) => x.value);
        this.props.el.classList.add("d-none");
    }

    onSelect(value) {
        this.state.value = value;
        this.props.el.value = value;
        // Manually trigger the change event
        const event = new Event("change", { bubbles: true });
        this.props.el.dispatchEvent(event);
    }
}

websiteSaleAddress.include({
    events: Object.assign(
        {},
        websiteSaleAddress.prototype.events,
        {
            'change .o_select_city': '_onChangeBrazilianCity',
        }
    ),

    start: async function () {
        this._super.apply(this, arguments);

        if (this.countryCode === "BR") {
            const selectEl = this.el.querySelector("select[name='city_id']");
            await attachComponent(this, selectEl.parentElement, SelectMenuWrapper, {
                el: selectEl,
            });
            this._changeCountry();
        }
    },

    _selectState: function(id) {
        this.addressForm.querySelector(`select[name="state_id"] > option[value="${id}"]`).selected = 'selected';
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
        if (this.countryCode === 'BR') {
            const countryOption = this.addressForm.country_id;
            const selectedCountryCode = countryOption.value ? countryOption.selectedOptions[0].getAttribute('code') : '';

            if (selectedCountryCode === 'BR') {
                this._setVisibility('.o_standard_address', false); // hide
                this._setVisibility('.o_extended_address', true); // show
            } else {
                this._setVisibility('.o_standard_address', true); // show
                this._setVisibility('.o_extended_address', false); // hide
            }
        }

        return res;
    },

    _onChangeBrazilianCity() {
        if (this.addressForm.city_id.value) {
            this._selectState(this.addressForm.city_id.querySelector(`option[value='${this.addressForm.city_id.value}']`).getAttribute('state-id'));
        }
    },
});
