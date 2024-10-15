/** @odoo-module **/

import websiteSaleAddress from "@portal/js/portal_address"

websiteSaleAddress.include({
    events: Object.assign(
        {},
        websiteSaleAddress.prototype.events,
        {
            'click #save_address': '_onSaveAddress',
            "change select[name='state_id']": "_onChangeState",
        }
    ),

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeState(ev) {
        return Promise.resolve();
    },

    /**
     * Disable the button, submit the form and add a spinner while the submission is ongoing
     *
     * @private
     * @override
     * @param {Event} ev
     */
    async _onSaveAddress(ev) {
        if (!this.addressForm.reportValidity()) {
            return
        }

        const submitButton = ev.currentTarget;
        if (!ev.defaultPrevented && !submitButton.disabled) {
            ev.preventDefault();

            submitButton.disabled = true;
            const spinner = document.createElement('span');
            spinner.classList.add('fa', 'fa-cog', 'fa-spin');
            submitButton.appendChild(spinner);
            const result = await this.http.post(
                '/shop/address/submit',
                new FormData(this.addressForm),
            );
            if (result.successUrl) {
                window.location = result.successUrl;
            } else {
                // Highlight missing/invalid form values
                document.querySelectorAll('.is-invalid').forEach(element => {
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

                // Re-enable button and remove spinner
                submitButton.disabled = false;
                spinner.remove();
            }
        }
    },

});

