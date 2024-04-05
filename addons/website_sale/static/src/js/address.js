/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";

publicWidget.registry.websiteSaleAddress = publicWidget.Widget.extend({
    // /shop/address
    selector: '.o_wsale_address_fill',
    events: {
        'change select[name="country_id"]': '_onChangeCountry',
        'change #shipping_use_same': '_onChangeShippingUseSame',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._changeCountry = debounce(this._changeCountry.bind(this), 500);
    },

    /**
     * @override
     */
    start() {
        const def = this._super(...arguments);

        const selectElement = this.el.querySelector('select[name="country_id"]');
        selectElement.dispatchEvent(new Event('change'));;

        return def;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCountry: function (ev) {
        if (!this.el.querySelector('.checkout_autoformat').length) {
            return;
        }
        return this._changeCountry();
    },

    /**
     * @private
     */
    _changeCountry: function () {
        if (!this.el.querySelector("#country_id").value) {
            return;
        }
        return rpc("/shop/country_infos/" + this.el.querySelector("#country_id").value, {
            mode: this.el.querySelector("#country_id").getAttribute('mode'),
        }).then(function (data) {
            // placeholder phone_code
            this.el.querySelector("input[name='phone']").setAttribute('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

            // populate states and display
            const selectStates = this.el.querySelector("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStates.dataset.init === 0 || selectStates.querySelector('option').length === 1) {
                if (data.states.length || data.state_required) {
                    selectStates.innerHTML = '';
                    data.states.forEach((x) => {
                        const opt = document.createElement('option');
                        opt.textContent = x[1];
                        opt.value = x[0];
                        opt.dataset.code = x[2];
                        selectStates.append(opt);
                    });
                    selectStates.closest('div').style.display = '';
                } else {
                    selectStates.value = '';
                    selectStates.parentNode.style.display = 'none';
                }
                selectStates.dataset.init = 0;
            } else {
                selectStates.dataset.init = 0;
            }

            // manage fields order / visibility
            if (data.fields) {
                let divZip = this.el.querySelector('.div_zip');
                let divCity = this.el.querySelector('.div_city');
                if (data.fields.indexOf('zip') > data.fields.indexOf('city')){
                    divZip.parentNode.insertBefore(divCity, divZip);
                } else {
                    divZip.parentNode.insertBefore(divCity, divZip.nextSibling);
                }
                var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                all_fields.forEach((field) => {
                    const fieldEl = field.querySelector(".checkout_autoformat .div_" + field.split('_')[0]);
                    fieldEl.style.display = data.fields.includes(field) ? '' : 'none';
                });
            }

            if (this.el.querySelector("label[for='zip']").length) {
                this.el.querySelector("label[for='zip']").classList.toggle('label-optional', !data.zip_required);
                this.el.querySelector("label[for='zip']").classList.setAttribute('required', !!data.zip_required);
            }
            if (this.el.querySelector("label[for='zip']").length) {
                this.el.querySelector("label[for='state_id']").classList.toggle('label-optional', !data.state_required);
                this.el.querySelector("label[for='state_id']").classList.setAttribute('required', !!data.state_required);
            }
        });
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeShippingUseSame: function (ev) {
        document.querySelector('.ship_to_other').style.display = ev.currentTarget.checked ? 'none' : '';
    },

});

export default publicWidget.registry.websiteSaleAddress;
