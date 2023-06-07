/** @odoo-module **/

import publicWidget from "web.public.widget";
import { _t } from "@web/core/l10n/translation";

var timeout;

publicWidget.registry.websiteSaleCartLink = publicWidget.Widget.extend({
    selector: '#top a[href$="/shop/cart"]:not(.js_change_lang)',
    events: {
        'mouseenter': '_onMouseEnter',
        'mouseleave': '_onMouseLeave',
        'click': '_onClick',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._popoverRPC = null;
        this._onVisibilityChange = this._onVisibilityChange.bind(this);
    },
    /**
     * @override
     */
    willStart() {
        return Promise.all([this._super.apply(this, arguments), this._updateCartQuantityValue()]);
    },
    /**
     * @override
     */
    start: function () {
        this.$el.popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return _t("My Cart");
            },
            container: 'body',
            placement: 'auto',
            template: '<div class="popover mycart-popover" role="tooltip"><div class="tooltip-arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>'
        });
        window.addEventListener('visibilitychange', this._onVisibilityChange);
        this._updateCartQuantityText();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy() {
        window.removeEventListener('visibilitychange', this._onVisibilityChange);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onMouseEnter: function (ev) {
        let self = this;
        self.hovered = true;
        clearTimeout(timeout);
        $(this.selector).not(ev.currentTarget).popover('hide');
        timeout = setTimeout(function () {
            if (!self.hovered || $('.mycart-popover:visible').length) {
                return;
            }
            self._popoverRPC = $.get("/shop/cart", {
                type: 'popover',
            }).then(function (data) {
                const popover = Popover.getInstance(self.$el[0]);
                popover._config.content = data;
                popover.setContent(popover.getTipElement());
                self.$el.popover("show");
                $('.popover').on('mouseleave', function () {
                    self.$el.trigger('mouseleave');
                });
                self.cartQty = +$(data).find('.o_wsale_cart_quantity').text();
                sessionStorage.setItem('website_sale_cart_quantity', self.cartQty);
                self._updateCartQuantityText();
            });
        }, 300);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseLeave: function (ev) {
        let self = this;
        self.hovered = false;
        setTimeout(function () {
            if ($('.popover:hover').length) {
                return;
            }
            if (!self.$el.is(':hover')) {
               self.$el.popover('hide');
            }
        }, 1000);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClick: function (ev) {
        // When clicking on the cart link, prevent any popover to show up (by
        // clearing the related setTimeout) and, if a popover rpc is ongoing,
        // wait for it to be completed before going to the link's href. Indeed,
        // going to that page may perform the same computation the popover rpc
        // is already doing.
        clearTimeout(timeout);
        if (this._popoverRPC && this._popoverRPC.state() === 'pending') {
            ev.preventDefault();
            var href = ev.currentTarget.href;
            this._popoverRPC.then(function () {
                window.location.href = href;
            });
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onVisibilityChange(ev) {
        if (ev.target.visibilityState === 'visible'){
            this._updateCartQuantityValue().then(this._updateCartQuantityText.bind(this));
        }
    },
    /**
     * @private
     */
    async _updateCartQuantityValue() {
        if ('website_sale_cart_quantity' in sessionStorage) {
            this.cartQty = sessionStorage.getItem('website_sale_cart_quantity');
        }
        if (this.el.querySelector('.my_cart_quantity')?.innerText != this.cartQty) {
            return this._rpc({route: "/shop/cart/quantity"}).then((cartQty) => {
                this.cartQty = cartQty;
                sessionStorage.setItem('website_sale_cart_quantity', this.cartQty);
            });
        }
    },
    /**
     * @private
     */
    _updateCartQuantityText() {
        if (this.cartQty !== undefined && this.el.querySelector('.my_cart_quantity')) {
            this.el.querySelector('.my_cart_quantity').innerText = this.cartQty;
        }
    }
});
