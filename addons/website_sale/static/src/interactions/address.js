import { markup } from '@odoo/owl';
import { CustomerAddress } from '@portal/interactions/address';
import { rpc } from '@web/core/network/rpc';
import { setElementContent } from '@web/core/utils/html';
import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { AlertBanner } from '@website_sale/js/components/alert_banner/alert_banner';

patch(CustomerAddress.prototype, {
    // /shop/address

    setup() {
        super.setup();
        // There is two main buttons in the DOM for mobile or desktop. User can switch from one mode
        // to the other by rotating their tablet.
        const submitButtons = document.getElementsByName('website_sale_main_button');
        const boundSaveAddress = this.saveAddress.bind(this);
        submitButtons.forEach(submitButton => {
            submitButton.addEventListener('click', boundSaveAddress);
            this.registerCleanup(() => submitButton.removeEventListener('click', boundSaveAddress));
        });
        // Display errors as nice alerts at the top of the checkout page.
        this.errorsDiv = document.getElementById('checkout_alerts') ?? this.errorsDiv;
        this.errorCleanups = [];
        this.addressFormFields = this.el.querySelector('#o_billing_address_form_fields');
        patchDynamicContent(this.dynamicContent, {
            '#o_billing_address_dropdown': { 't-on-change': this.onChangeBillingAddress.bind(this) },
        });
    },

    _replaceErrorMessages(messages) {
        this._cleanupErrorComponents();
        super._replaceErrorMessages(messages);
    },

    _renderErrorMessage(message) {
        this.errorCleanups.push(
            this.mountComponent(this.errorsDiv, AlertBanner, {level: 'danger', message})
        );
    },

    _cleanupErrorComponents() {
        this.errorCleanups.forEach(cleanup => cleanup());
        this.errorCleanups = [];
    },

    /**
     * Fill the address form fields with the selected billing address, or empty them to create a
     * new address if no address is selected.
     *
     * @param {Event} ev
     * @return {void}
     */
    async onChangeBillingAddress(ev) {
        const partnerId = ev.target.value;
        const {
            billing_address_form_fields: addressFormFieldsHtml,
            billing_address_required_fields: requiredFields,
        } = await this.waitFor(rpc(
            '/shop/payment/billing_address_form_fields', { partner_id: partnerId || null }
        ));
        // The address form fields are regenerated below, so we need to stop and start interactions
        // to make sure the regenerated fields are properly handled.
        this.services['public.interactions'].stopInteractions(this.addressForm);
        setElementContent(this.addressFormFields, markup(addressFormFieldsHtml));
        // The required fields depend on the address (e.g. its country).
        this.addressForm.dataset.defaultRequiredFields = requiredFields;
        this.services['public.interactions'].startInteractions(this.addressForm);
        // This interaction is not restarted as its element is a parent of the form, so the
        // regenerated fields must be marked as required here.
        this.requiredFields = requiredFields.split(',');
        this.alwaysRequiredFields = this.addressForm.required_fields.value.split(',');
        [...this.requiredFields, ...this.alwaysRequiredFields].forEach(
            fieldName => this._markRequired(fieldName, true)
        );
        this._updateAddressLayout();
    }
});
