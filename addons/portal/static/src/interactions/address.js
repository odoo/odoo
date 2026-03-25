import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import { redirect } from '@web/core/utils/urls';

export class CustomerAddress extends Interaction {
    // /my/address & /my/account
    static selector = '.o_customer_address_fill';
    dynamicContent = {
        'select[name="country_id"]': { 't-on-change': this.debounced(this.onChangeCountry, 500) },
        "select[name='city_id']": { "t-on-change": this.debounced(this.onChangeCity, 500) },
        "select[name='state_id']": { "t-on-change": this.debounced(this.onChangeState, 500) },
        'input[name="zip"]': { 't-on-input': this.onChangeZip.bind(this) },
        '#save_address': { 't-on-click.prevent': this.locked(this.saveAddress, true) },
    };

    setup() {
        this.http = this.services['http'];
        this.addressForm = this.el.querySelector('form.address_autoformat');
        this.errorsDiv = this.el.querySelector('#errors');
        this.addressType = this.addressForm['address_type'].value;
        this.useDeliveryAsBilling = this.addressForm.use_delivery_as_billing.value;
        this.countryCode = this.addressForm.dataset.companyCountryCode;

        // Required fields (defined server-side)
        this.requiredFields = this.addressForm.dataset.requiredFields?.split(",") || [];
        this.requiredFields.forEach((fieldName) => this._markRequired(fieldName, true));

        // Support for customizations and additional required fields
        this.alwaysRequiredFields = this.addressForm.required_fields.value.split(",");
        this.alwaysRequiredFields.forEach((fieldName) => this._markRequired(fieldName, true));
    }

    async onChangeCountry() {
        const countryId = parseInt(this.addressForm.country_id.value);
        if (!countryId) return;

        const data = await this.waitFor(rpc(
            `/my/address/country_info/${countryId}`,
            {
                address_type: this.addressType,
                use_delivery_as_billing: this.useDeliveryAsBilling,
            },
        ));

        this.addressForm.phone.placeholder = data.phone_code;
        // manage fields order / visibility
        if (data.address_fields) {
            const cityField = data.required_fields.includes("city_id") ? "city_id" : "city";
            if (data.zip_before_city) {
                this._getInputDiv("zip").after(this._getInputDiv(cityField));
            } else {
                this._getInputDiv("zip").before(this._getInputDiv(cityField));
            }

            const addressFields = this._getAddressFields();
            addressFields.forEach((fname) => {
                if (data.address_fields.includes(fname)) {
                    if (data.selection && fname in data.selection) {
                        // Configure the options for relational fields
                        this._setFieldChoices(fname, data.selection[fname].data);
                    }
                    if (!data.selection?.[fname]) {
                        this._showInput(fname);
                    }
                } else {
                    this._hideInput(fname);
                }
            });
        }

        // add requirement on new required fields
        data.required_fields.forEach((fieldName) => {
            this._markRequired(fieldName, true);
        })
        const required_fields = this.addressForm.querySelectorAll(":required");
        required_fields.forEach((element) => {
            // remove requirement on previously required fields
            if (
                !data.required_fields.includes(element.name)
                && !this.alwaysRequiredFields.includes(element.name)
            ) {
                this._markRequired(element.name, false);
            }
        });

        return data;
    }

    _getAddressFields() {
        return new Set(["street", "zip", "state_id", "city", "city_id"]);
    }

    async onChangeState() {
        const data = await this.waitFor(rpc(`/my/address/state_info`, {
            country_id: parseInt(this.addressForm.country_id.value),
            state_id: parseInt(this.addressForm.state_id.value),
        }));
        if (data.cities) {
            this._setFieldChoices('city_id', data.cities);
        }

        return data;
    }

    /*
     * Auto-fill zip code according to chosen city
     */
    async onChangeCity() {
        const cityZipCode = this.addressForm.city_id.selectedOptions[0].dataset.zipcode;

        if (cityZipCode) {
            this.addressForm.zip.value = cityZipCode;
        }
    }

    /**
     * Overridable hook.
     */
    async onChangeZip() {}

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

    _hideInput(name, clearValue=true) {
        // hide parent div, containing label and input
        this.addressForm[name].parentElement.style.display = 'none';
        if (!clearValue) return;
        this.addressForm[name].value = ''
    }

    _markRequired(name, required) {
        const input = this.addressForm[name];
        if (input) {
            input.required = required;
        }
        this._getInputLabel(name)?.classList.toggle('label-optional', !required);
    }

    _setFieldChoices(name, data_list) {
        const selection = this.addressForm[name];
        // empty existing options, only keep the first-choice placeholder.
        selection.options.length = 1;

        if (!data_list.length) {
            this._hideInput(name);
            return
        }
        // create new options and append them to the select element
        data_list.forEach((choice) => {
            const option = new Option(choice.name, choice.id);
            Object.keys(choice).forEach((key) => {
                if (!['name', 'id'].includes(key) && choice[key]) {
                    option.dataset[key] = choice[key];
                }
            });
            selection.appendChild(option);
        });
        this._showInput(name);
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
            this._replaceErrorMessages(result.messages);
        }
    }

    _replaceErrorMessages(messages) {
        this.errorsDiv.replaceChildren();
        messages.forEach(this._renderErrorMessage.bind(this));
    }

    _renderErrorMessage(message) {
        const errorHeader = document.createElement('h5');
        errorHeader.classList.add('text-danger');
        errorHeader.appendChild(document.createTextNode(message));
        this.errorsDiv.appendChild(errorHeader);
    }

    /**
     * Gets the selected country code.
     *
     * Used in overrides.
     */
    _getSelectedCountryCode() {
        const country = this.addressForm.country_id;
        return country.value ? country.selectedOptions[0].dataset.code : '';
    }
}

registry
    .category('public.interactions')
    .add('portal.customer_address', CustomerAddress);
