import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { rpc } from "@web/core/network/rpc";


export class SupportedPaymentMethods extends Interaction {
    static selector = ".s_supported_payment_methods";

    setup() {
        this.payment_methods = [];
        this.templateKey = "website_payment.s_supported_payment_methods.icons";
    }

    async willStart() {
        await this._fetchPaymentMethods();
    }

    start() {
        this.render();
    }

    get limit() { return this.el.dataset.limit || 6; }

    get height() { return this.el.dataset.height || 30; }

    async _fetchPaymentMethods() {
        this.payment_methods = await this.waitFor(rpc(
            "/website_payment/snippet/supported_payment_methods", { limit: this.limit },
        )).catch(_ => []);
    }

    async render() {
        // If the snippet is empty, a <br> tag is added by default
        this.el.replaceChildren();
        this.renderAt(
            this.templateKey,
            { payment_methods: this.payment_methods, height: this.height },
            this.el,
        );
    }
}

registry
    .category("public.interactions")
    .add("website_sale.supported_payment_methods", SupportedPaymentMethods);
