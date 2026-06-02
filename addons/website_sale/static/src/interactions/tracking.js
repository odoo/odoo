import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class Tracking extends Interaction {
    static selector = '.oe_website_sale';
    dynamicContent = {
        'a[href^="/shop/checkout"]': { 't-on-click': this.onCheckoutStart },
        'a[href^="/web/login?redirect"][href*="/shop/checkout"]': {
            't-on-click': this.onCustomerSignin,
        },
        'a[href="/shop/payment"]': { 't-on-click': this.onOrder },
        'button[name="o_payment_submit_button"]': { 't-on-click': this.onOrderPayment },
        _root: {
            't-on-view_item_event': (ev) => this.onViewItem(ev),
            "t-on-select_item_event": (ev) => this.onSelectItem(ev),
            't-on-add_to_cart_event': (ev) => this.onAddToCart(ev),
            "t-on-update_cart_event": (ev) => this.onUpdateCart(ev),
            "t-on-add_shipping_info_event": (ev) => this.onAddShippingInfo(ev),
            "t-on-add_to_wishlist_event": (ev) => this.onAddToWishlist(ev),
        },
    };

    setup() {
        const confirmation = this.el.querySelector('div[name="order_confirmation"]');
        if (confirmation) {
            this._vpv('/stats/ecom/order_confirmed/' + confirmation.dataset.orderId);
            this._trackGa('event', 'purchase', JSON.parse(confirmation.dataset.orderTrackingInfo));
        }

        const cartTrackingEl = this.el.querySelector("#cart_tracking_info");
        if (cartTrackingEl?.dataset?.cartTrackingInfo) {
            const cartTrackingData = JSON.parse(cartTrackingEl.dataset.cartTrackingInfo);
            delete cartTrackingData.coupon;
            this._trackGa(
                "event",
                "view_cart",
                cartTrackingData,
            );
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
        const { trackingInfo, currency } = event.detail;
        this._trackGa("event", "view_item", {
            currency,
            value: trackingInfo.price,
            items: [trackingInfo],
        });
    }

    onSelectItem(event) {
        const { item_list_name, trackingInfo } = event.detail;
        this._trackGa("event", "select_item", {
            item_list_name,
            items: [trackingInfo],
        });
    }

    _trackCartEvent(eventName, currency, items) {
        this._trackGa("event", eventName, {
            currency,
            value: items.reduce((acc, item) => acc + item.price * item.quantity, 0),
            items,
        });
    }

    onAddToCart(event) {
        const { currency, items } = event.detail;
        if (!items?.length) return;
        this._trackCartEvent(
            "add_to_cart",
            currency,
            items.map(({ delta_quantity, ...item }) => item),
        );
    }

    onUpdateCart(event) {
        const { currency, items } = event.detail;
        if (!items?.length) return;
        const added = items.filter(i => i.delta_quantity > 0).map(({ delta_quantity, ...i }) => i);
        const removed = items.filter(i => i.delta_quantity < 0).map(({ delta_quantity, ...i }) => i);
        if (added.length) this._trackCartEvent("add_to_cart", currency, added);
        if (removed.length) this._trackCartEvent("remove_from_cart", currency, removed);
    }

    onCheckoutStart() {
        this._vpv('/stats/ecom/customer_checkout');
        const cartTrackingEl = this.el.querySelector("#cart_tracking_info");
        if (!cartTrackingEl?.dataset?.cartTrackingInfo) return;
        this._trackGa("event", "begin_checkout",
            JSON.parse(cartTrackingEl.dataset.cartTrackingInfo)
        );
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

        const paymentTrackingElement = this.el.querySelector("#payment_tracking_info");
        const trackingInfo = paymentTrackingElement?.dataset?.paymentTrackingInfo
            ? JSON.parse(paymentTrackingElement.dataset.paymentTrackingInfo)
            : {};

        this._trackGa("event", "add_payment_info", {
            ...trackingInfo,
            payment_type: paymentMethod,
        });
    }

    onAddShippingInfo(event) {
        const shippingInfo = event.detail;
        if (!shippingInfo) return;
        this._trackGa("event", "add_shipping_info", shippingInfo);
    }

    onAddToWishlist(event) {
        const { trackingInfo, currency } = event.detail;
        if (!trackingInfo) return;
        this._trackGa("event", "add_to_wishlist", {
            currency,
            value: trackingInfo.price,
            items: [trackingInfo],
        });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.tracking', Tracking);
