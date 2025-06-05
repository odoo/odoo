import { browser } from '@web/core/browser/browser';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';


export class SupportedPaymentMethods extends Interaction {
    static selector = '.s_supported_payment_methods';

    setup() {
        this.payment_methods = [];
        this.templateKey = 'website_payment.s_supported_payment_methods.icons';
    }

    async willStart() {
        await this.fetchPaymentMethods();
    }

    /**
     * Fetch the payment methods and cache them in the session.
     *
     * Caching limits the amount of rpc calls when switching pages, or when editing the snippet in
     * the editor as any edit reloads the interaction.
     */
    async fetchPaymentMethods() {
        let cache = JSON.parse(
            browser.sessionStorage.getItem('website_payment.supported_payment_methods') || '{}',
        );

        // Re-fetch if the cached list can potentially be larger
        if (cache.payment_methods === undefined || cache.limit < this.limit) {
            cache.payment_methods = await this.waitFor(
                rpc('/website_payment/snippet/supported_payment_methods', { limit: this.limit }),
            ).catch(_ => []);
            cache.limit = this.limit;
            browser.sessionStorage.setItem(
                'website_payment.supported_payment_methods', JSON.stringify(cache),
            );
        }

        this.payment_methods = cache.payment_methods.slice(0, this.limit);
    }

    start() {
        this.el.replaceChildren();
        this.renderAt(
            this.templateKey,
            { payment_methods: this.payment_methods, height: this.height },
            this.el,
        );
    }

    get limit() { return parseInt(this.el.dataset.limit) || 6; }

    get height() { return parseInt(this.el.dataset.height) || 30; }
}

registry
    .category('public.interactions')
    .add('website_sale.supported_payment_methods', SupportedPaymentMethods);
