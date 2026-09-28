
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class BillingAddressForm extends Interaction {
    static selector = "#billing_address_form";
    dynamicContent = {
        "#use_delivery_as_billing": { "t-on-change": this._onChangeUseDeliveryAsBilling.bind(this) },
        "#use_different_billing_address": { "t-on-change": this._onChangeUseDeliveryAsBilling.bind(this) },
        "#set_invoice_address_input": { "t-on-change": this._onChangeUseDeliveryAsBilling.bind(this) },
    }

    _onChangeUseDeliveryAsBilling() {
        const billingAddressFormContainer = document.getElementById("billing_address_form_container");
        billingAddressFormContainer.classList.toggle("d-none", !this._canShowBillingAddressForm());
    }

    _canShowBillingAddressForm() {
        const useDifferentBillingAddressRadio = document.getElementById("use_different_billing_address");
        const sendInvoiceCheckbox = document.getElementById("set_invoice_address_input");
        return (useDifferentBillingAddressRadio?.checked || sendInvoiceCheckbox?.checked);
    }


}

registry.category("public.interactions").add("website_sale.billing_address_form", BillingAddressForm);