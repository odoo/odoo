import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteSaleExtraInfo = publicWidget.Widget.extend({
    // /shop/extra_info
    selector: '#class_extra_info',

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.http = this.bindService('http');

        this.submitButton = document.getElementById('save_extra_info')
        this._boundSaveExtraInfo = this._onSaveExtraInfo.bind(this);
        this.submitButton.addEventListener("click", this._boundSaveExtraInfo);
        this.extraForm = document.querySelector('form.form_extra_info');
    },

    destroy() {
        this.submitButton.removeEventListener("click", this._boundSaveExtraInfo);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Disable the button, submit the form and add a spinner while the submission is ongoing
     *
     * @private
     * @param {Event} ev
     */
    async _onSaveExtraInfo(ev) {
        if (!this.extraForm.reportValidity()) {
            return
        }
        const submitButton = ev.currentTarget;
        if (!ev.defaultPrevented && !submitButton.disabled) {
            ev.preventDefault();

            submitButton.disabled = true;
            const spinner = document.createElement('span');
            spinner.classList.add('fa', 'fa-cog', 'fa-spin');
            submitButton.appendChild(spinner);

            const formData = new FormData(this.extraForm);

            const attachmentInput = document.getElementById("sale3");
            if (attachmentInput.files.length === 0) {
                // Avoid sending an empty file
                formData.delete("a_document");
            }
            const result = await this.http.post(
                '/website/form/shop.sale.order',
                formData,
            )
            // no errors
            if (result.id) {
                window.location = '/shop/confirm_order';
            } else {
                // Re-enable button and remove spinner
                submitButton.disabled = false;
                spinner.remove();
            }
        }
    },
});

export default publicWidget.registry.websiteSaleExtraInfo;
