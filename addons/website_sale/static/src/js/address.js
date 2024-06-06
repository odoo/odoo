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

        const selectElement = this.el.querySelector("select[name='country_id']");
        selectElement.dispatchEvent(new Event("change", { bubbles: true }));

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
        if (!this.el.querySelector(".checkout_autoformat")) {
            return;
        }
        return this._changeCountry();
    },

    /**
     * @private
     */
    _changeCountry: function () {
        const countryEl = this.el.querySelector("#country_id");
        if (!countryEl.value) {
            return;
        }
        return rpc("/shop/country_infos/" + countryEl.value, {
            mode: countryEl.getAttribute("mode"),
        }).then((data) => {
            // placeholder phone_code
            this.el
                .querySelector("input[name='phone']")
                .setAttribute("placeholder", data.phone_code !== 0 ? "+" + data.phone_code : "");

            // populate states and display
            const selectStateEl = this.el.querySelector("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStateEl.getDataset("init") === 0 ||
                selectStateEl.querySelectorAll("option").length === 1
            ) {
                if (data.states.length || data.state_required) {
                    selectStateEl.innerHTML = "";
                    data.states.forEach((x) => {
                        const optionEl = document.createElement("option");
                        optionEl.textContent = x[1];
                        optionEl.value = x[0];
                        optionEl.dataset.code = x[2];
                        selectStateEl.append(optionEl);
                    });
                    selectStateEl.closest("div").style.display = "";
                } else {
                    selectStateEl.value = "";
                    selectStateEl.parentNode.style.display = "none";
                }
                selectStateEl.dataset.init = 0;
            } else {
                selectStateEl.dataset.init = 0;
            }

            // manage fields order / visibility
            if (data.fields) {
                const divZipEL = this.el.querySelector(".div_zip");
                const divCityEl = this.el.querySelector(".div_city");
                if (data.fields.indexOf("zip") > data.fields.indexOf("city")) {
                    divZipEL.parentNode.insertBefore(divCityEl, divZipEL);
                } else {
                    divZipEL.parentNode.insertBefore(divCityEl, divZipEL.nextSibling);
                }
                var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                all_fields.forEach((field) => {
                    const fieldEl = this.el.querySelector(
                        ".checkout_autoformat .div_" + field.split("_")[0]
                    );
                    fieldEl.style.display = data.fields.includes(field) ? "" : "none";
                });
            }

            const lableZipEl = this.el.querySelector("label[for='zip']");
            if (lableZipEl) {
                lableZipEl.classList.toggle("label-optional", !data.zip_required);
                lableZipEl.setAttribute("required", !!data.zip_required);
            }
            if (lableZipEl) {
                const lableStateIdEl = this.el.querySelector("label[for='state_id']");
                lableStateIdEl.classList.toggle("label-optional", !data.state_required);
                lableStateIdEl.setAttribute("required", !!data.state_required);
            }
        });
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeShippingUseSame: function (ev) {
        if (this.el.querySelector(".ship_to_other")) {
            this.el.querySelector(".ship_to_other").style.display = ev.currentTarget.checked
                ? "none"
                : "";
        }
    },

});

export default publicWidget.registry.websiteSaleAddress;
