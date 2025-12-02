import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class Tracking extends Interaction {
    static selector = '.oe_website_sale';
    dynamicContent = {
        'form a.a-submit': { 't-on-click': this.onAddProductToCart },
        'a[href^="/shop/checkout"]': { 't-on-click': this.onCheckoutStart },
        'a[href^="/web/login?redirect"][href*="/shop/checkout"]': {
            't-on-click': this.onCustomerSignin,
        },
        'a[href="/shop/payment"]': { 't-on-click': this.onOrder },
        'button[name="o_payment_submit_button"]': { 't-on-click': this.onOrderPayment },
        _root: {
            't-on-view_item_event': (ev) => this.onViewItem(ev),
            't-on-add_to_cart_event': (ev) => this.onAddToCart(ev),
        },
    };

    setup() {
        const confirmation = this.el.querySelector('div[name="order_confirmation"]');
        if (confirmation) {
            this._vpv('/stats/ecom/order_confirmed/' + confirmation.dataset.orderId);
            this._trackGa('event', 'purchase', confirmation.dataset.orderTrackingInfo);
        }
    }

    /**
     * @private
     */
    _trackGa() {
        const websiteGA = window.gtag || (() => {});
        websiteGA.apply(this, arguments);
    }

    /**
     * Virtual page view
     *
     * @private
     */
    _vpv(page) {
        this._trackGa('event', 'page_view', { 'page_path': page });
    }

    onViewItem(event) {
        const productTrackingInfo = event.detail;
        const trackingInfo = {
            'currency': productTrackingInfo['currency'],
            'value': productTrackingInfo['price'],
            'items': [productTrackingInfo],
        };
        this._trackGa('event', 'view_item', trackingInfo);
    }

    onAddToCart(event) {
        const productsTrackingInfo = event.detail;
        const trackingInfo = {
            'currency': productsTrackingInfo[0]['currency'],
            'value': productsTrackingInfo.reduce(
                (acc, val) => acc + val['price'] * val['quantity'], 0
            ),
            'items': productsTrackingInfo,
        };
        this._trackGa('event', 'add_to_cart', trackingInfo);
    }

    onAddProductToCart() {
        const productId = this.el.querySelector('input[name="product_id"]')?.getAttribute('value');
        if (productId) {
            this._vpv('/stats/ecom/product_add_to_cart/' + productId);
        }
    }

    onCheckoutStart() {
        this._vpv('/stats/ecom/customer_checkout');
    }

    onCustomerSignin() {
        this._vpv('/stats/ecom/customer_signin');
    }

    onOrder() {
        if (document.querySelector('header#top [href="/web/login"]')) {
            this._vpv('/stats/ecom/customer_signup');
        }
        this._vpv('/stats/ecom/order_checkout');
    }

    onOrderPayment() {
        const paymentMethod = this.el.querySelector(
            '#payment_method input[name="o_payment_radio"]:checked'
        )?.parentElement?.querySelector('.o_payment_option_label')?.textContent;
        this._vpv('/stats/ecom/order_payment/' + paymentMethod);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.tracking', Tracking);
