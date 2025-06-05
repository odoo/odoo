import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";


class SupportedPaymentMethodsEdit extends Interaction {
    static selector = ".s_supported_payment_methods[data-empty=true]";
    dynamicContent = {
        // Bypass the ctrl-click required to open a link in edit mode
        ".btn-view_providers": { "t-on-click": this.onClickViewPorviders.bind(this) },
    };

    start() {
        this.render();
    }

    /**
     * Displays a message when no payment methods could be found (will not be saved by the editor).
     */
    render() {
        this.el.replaceChildren();
        this.renderAt(
            "website_payment.s_supported_payment_methods.view_providers",
            {},
            this.el,
            // removeOnClean = true,  // by default
        );
    }

    async onClickViewPorviders(ev) {
        // Opens the view in a seperate tab such that any edit are kept
        browser.open("/odoo/action-payment.action_payment_provider");
    }
};


registry
    .category("public.interactions.edit")
    .add("website.supported_payment_methods", { Interaction: SupportedPaymentMethodsEdit });
