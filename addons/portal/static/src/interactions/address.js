import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import { redirect } from '@web/core/utils/urls';

export class CustomerAddress extends Interaction {
    // /my/address & /my/account
    static selector = '.o_customer_address_fill';
    dynamicContent = {
        'select[name="country_id"]': { 't-on-change': this.debounced(this.onChangeCountry, 500) },
        'select[name="state_id"]': { 't-on-change': this.onChangeState },
        '#save_address': { 't-on-click.prevent': this.locked(this.saveAddress, true) },
    };

    setup() {
        this.http = this.services['http'];
        this.addressForm = this.el.querySelector('form.address_autoformat');
        this.errorsDiv = this.el.querySelector('#errors');
        this.addressType = this.addressForm['address_type'].value;
        this.countryCode = this.addressForm.dataset.companyCountryCode;
        this.requiredFields = this.addressForm.required_fields.value.split(',');
        this.requiredFields.forEach((fieldName) => this._markRequired(fieldName, true));
    }

    async willStart() {
        await this._onChangeCountry(true);
    }

    async onChangeCountry() {
        return this._onChangeCountry();
    }

    /**
     * Overridable hook.
     */
    async onChangeState() {}

    async _onChangeCountry(init=false) {
        const countryId = parseInt(this.addressForm.country_id.value);
        if (!countryId) return;

        const data = await this.waitFor(rpc(
            `/my/address/country_info/${countryId}`,
            {address_type: this.addressType},
        ));

        this.addressForm.phone.placeholder = data.phone_code !== 0 ? `+${data.phone_code}` : '';

        // populate states and display
        const selectStates = this.addressForm.state_id;
        if (!init || selectStates.options.length === 1) {
            // dont reload state at first loading (done in qweb)
            if (data.states.length || data.state_required) {
                // empty existing options, only keep the placeholder.
                selectStates.options.length = 1;

                // create new options and append them to the select element
                data.states.forEach((state) => {
                    const option = new Option(state[1], state[0]);
                    // Used by localizations
                    option.setAttribute('data-code', state[2]);
                    selectStates.appendChild(option);
                });
                this._showInput('state_id');
            } else {
                this._hideInput('state_id');
            }
        }

        // manage fields order / visibility
        if (data.fields) {
            if (data.zip_before_city) {
                this._getInputDiv('zip').after(this._getInputDiv('city'));
            } else {
                this._getInputDiv('zip').before(this._getInputDiv('city'));
            }

            const all_fields = ['street', 'zip', 'city'];
            all_fields.forEach((fname) => {
                if (data.fields.includes(fname)) {
                    this._showInput(fname);
                } else {
                    this._hideInput(fname);
                }
            });
        }

        const required_fields = this.addressForm.querySelectorAll(':required');
        required_fields.forEach((element) => {
            // remove requirement on previously required fields
            if (
                !data.required_fields.includes(element.name)
                && !this.requiredFields.includes(element.name)
            ) {
                this._markRequired(element.name, false);
            }
        });
        data.required_fields.forEach((fieldName) => {
            this._markRequired(fieldName, true);
        })
    }

    _getInputDiv(name) {
        return this.addressForm[name].parentElement;
    }

    _getInputLabel(name) {
        const input = this.addressForm[name];
        return input?.parentElement.querySelector(`label[for='${input.id}']`);
    }

    _showInput(name) {
        // show parent div, containing label and input
        this.addressForm[name].parentElement.style.display = '';
    }

    _hideInput(name) {
        // show parent div, containing label and input
        this.addressForm[name].parentElement.style.display = 'none';
    }

    _markRequired(name, required) {
        const input = this.addressForm[name];
        if (input) {
            input.required = required;
        }
        this._getInputLabel(name)?.classList.toggle('label-optional', !required);
    }

    /**
     * Disable the button, submit the form and add a spinner while the submission is ongoing.
     *
     * @param {Event} ev
     */
    async saveAddress(ev) {
        ev.preventDefault();  // avoid potential redirect if href set on link
        if (!this.addressForm.reportValidity()) return;

        const result = await this.waitFor(this.http.post(
            this.addressForm.dataset.submitUrl,
            new FormData(this.addressForm),
        ))
        if (result.redirectUrl) {
            redirect(result.redirectUrl);
        } else {
            // Highlight missing/invalid form values
            this.el.querySelectorAll('.is-invalid').forEach(element => {
                if (!result.invalid_fields.includes(element.name)) {
                    element.classList.remove('is-invalid');
                }
            })
            result.invalid_fields.forEach(
                fieldName => this.addressForm[fieldName].classList.add('is-invalid')
            );

            // Display the error messages
            // NOTE: setCustomValidity is not used as we would have to reset the error msg on
            // input update, which is not worth catching for the rare cases where the
            // server-side validation will catch validation issues (now that required inputs
            // are also handled client-side)
            const newErrors = result.messages.map(message => {
                const errorHeader = document.createElement('h5');
                errorHeader.classList.add('text-danger');
                errorHeader.appendChild(document.createTextNode(message));
                return errorHeader;
            });

            this.errorsDiv.replaceChildren(...newErrors);
        }
    }

    /**
     * Gets the selected country code.
     *
     * Used in overrides.
     */
    _getSelectedCountryCode() {
        const country = this.addressForm.country_id;
        return country.value ? country.selectedOptions[0].getAttribute('code') : '';
    }
}

registry
    .category('public.interactions')
    .add('portal.customer_address', CustomerAddress);
