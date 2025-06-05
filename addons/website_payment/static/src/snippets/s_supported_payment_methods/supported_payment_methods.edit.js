import { SupportedPaymentMethods } from "./supported_payment_methods";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";


const SupportedPaymentMethodsEdit = I => class extends I {
    dynamicContent = {
        ".btn-view_providers": {
            "t-on-click": this.onClickViewPorviders.bind(this),
        },
    };

    /**
     * @override To display a message when no payment methods could be found.
     */
    render() {
        if (this.payment_methods.length) {
            return super.render();
        }
        // If the snippet is empty, a <br> tag is added by default
        this.el.replaceChildren();
        this.renderAt(
            "website_payment.s_supported_payment_methods.view_providers",
            {},
            this.el,
        );
    }

    async onClickViewPorviders(ev) {
        // Opens the view in a seperate tab such that any edit are kept
        browser.open("/odoo/action-payment.action_payment_provider");
    }
};

registry
    .category("public.interactions.edit")
    .add("website.supported_payment_methods", {
        Interaction: SupportedPaymentMethods,
        mixin: SupportedPaymentMethodsEdit,
    });
