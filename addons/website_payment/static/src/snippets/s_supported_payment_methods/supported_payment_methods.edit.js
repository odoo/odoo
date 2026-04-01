import { SupportedPaymentMethods } from './supported_payment_methods';
import { registry } from '@web/core/registry';
import { browser } from '@web/core/browser/browser';


const SupportedPaymentMethodsEdit = I => class extends I {
    dynamicContent = {
        // Bypass the ctrl-click required to open a link in edit mode.
        '.o_wpay_view_providers_btn': { 't-on-click': this.onClickViewProviders.bind(this) },
    };

    /**
     * @override To display an alert when no payment methods could be found.
     */
    setup() {
        super.setup();
        this.templateKey = 'website_payment.s_supported_payment_methods.no_payment_methods_alert';
    }

    async onClickViewProviders() {
        // Open the view in a separate tab such that any edits are kept.
        browser.open('/odoo/action-payment.action_payment_provider', '_blank');
    }
};

registry
    .category('public.interactions.edit')
    .add('website.supported_payment_methods', {
        Interaction: SupportedPaymentMethods,
        mixin: SupportedPaymentMethodsEdit,
    });
